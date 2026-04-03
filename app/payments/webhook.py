from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import AsyncSessionLocal
from models.order import Order, OrderStatus, Payment, PaymentStatus
from models.webhook import WebhookEvent

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_signature(body: dict, received_sign: str, api_key: str) -> bool:
    """Verify Cryptomus webhook signature.

    Cryptomus signs webhooks as:
        md5( base64_encode( json_encode(body_without_sign, JSON_UNESCAPED_UNICODE) ) + API_KEY )
    Forward-slashes must be escaped as \\/ in the JSON string.
    """
    json_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    json_str = json_str.replace("/", "\\/")
    encoded = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
    expected = hashlib.md5((encoded + api_key).encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected, received_sign)


async def _send_telegram_message(telegram_id: int, text: str) -> None:
    """Fire-and-forget Telegram message send; imported lazily to avoid circular deps."""
    from bot.utils import send_message_to_user
    try:
        await send_message_to_user(telegram_id, text)
    except Exception as exc:
        logger.error("Failed to send Telegram message to %s: %s", telegram_id, exc)


@router.post("/payments/cryptomus/webhook")
async def cryptomus_webhook(request: Request) -> Response:
    from config import settings

    raw_body = await request.body()

    # Parse JSON
    try:
        data: dict = json.loads(raw_body)
    except Exception:
        logger.warning("Cryptomus webhook: invalid JSON body")
        return Response(status_code=400, content="Invalid JSON")

    # Log to WebhookEvent
    async with AsyncSessionLocal() as session:
        event = WebhookEvent(
            source="cryptomus",
            event_type=data.get("status"),
            payload=data,
            processed=False,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        event_id = event.id

    # Signature verification
    received_sign = data.pop("sign", None)
    if not received_sign or not _verify_signature(data, received_sign, settings.cryptomus_api_key):
        logger.warning(
            "Cryptomus webhook: signature mismatch for event_id=%s payload=%s",
            event_id,
            data,
        )
        async with AsyncSessionLocal() as session:
            ev = await session.get(WebhookEvent, event_id)
            if ev:
                ev.error_message = "Signature verification failed"
                await session.commit()
        return Response(status_code=401, content="Signature mismatch")

    # Only process final webhooks
    is_final = data.get("is_final")
    if not is_final or str(is_final).lower() in ("false", "0", ""):
        return Response(status_code=200, content="ok")

    status = data.get("status", "")
    invoice_uuid = data.get("uuid")

    if not invoice_uuid:
        return Response(status_code=200, content="ok")

    async with AsyncSessionLocal() as session:
        # Find payment by cryptomus invoice uuid
        result = await session.execute(
            select(Payment)
            .where(Payment.cryptomus_invoice_id == invoice_uuid)
            .options(
                selectinload(Payment.order).selectinload(Order.telegram_user)
            )
        )
        payment = result.scalar_one_or_none()

        if not payment:
            logger.warning("Cryptomus webhook: no payment found for uuid=%s", invoice_uuid)
            return Response(status_code=200, content="ok")

        order = payment.order
        now = datetime.now(timezone.utc)

        # Idempotency: skip if already in terminal state
        if order.status in (
            OrderStatus.processing,
            OrderStatus.completed,
            OrderStatus.cancelled_expired,
        ):
            return Response(status_code=200, content="ok")

        if status in ("paid", "paid_over"):
            # On-time vs late logic
            expires_at = payment.expires_at
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at and now <= expires_at:
                payment.status = PaymentStatus.paid_on_time
                payment.paid_at = now
                order.status = OrderStatus.processing

                # Fetch fulfillment ETA from settings
                from sqlalchemy import select as sa_select
                from models.config import Setting
                eta_row = await session.execute(
                    sa_select(Setting).where(Setting.key == "fulfillment_eta")
                )
                eta_setting = eta_row.scalar_one_or_none()
                fulfillment_eta = eta_setting.value if eta_setting else "Completed within 1–4 hours"

                # Fetch processing template
                from models.config import MessageTemplate
                tmpl_row = await session.execute(
                    sa_select(MessageTemplate).where(MessageTemplate.slug == "processing")
                )
                tmpl = tmpl_row.scalar_one_or_none()
                if tmpl:
                    msg_text = tmpl.body_text.format(
                        order_id=order.id,
                        fulfillment_eta=fulfillment_eta,
                    )
                else:
                    msg_text = (
                        f"✅ Order #{order.id} — Payment Received!\n\n"
                        f"Status: Processing\n{fulfillment_eta}\n\n"
                        "We'll send your RDP credentials shortly."
                    )

                telegram_id = order.telegram_user.telegram_id
            else:
                payment.status = PaymentStatus.paid_late
                payment.paid_at = now
                order.status = OrderStatus.manual_review

                # Fetch support contact
                from sqlalchemy import select as sa_select
                from models.config import Setting, MessageTemplate
                sc_row = await session.execute(
                    sa_select(Setting).where(Setting.key == "support_contact")
                )
                sc_setting = sc_row.scalar_one_or_none()
                support_contact = sc_setting.value if sc_setting else "@support"

                tmpl_row = await session.execute(
                    sa_select(MessageTemplate).where(MessageTemplate.slug == "manual_review")
                )
                tmpl = tmpl_row.scalar_one_or_none()
                if tmpl:
                    msg_text = tmpl.body_text.format(
                        order_id=order.id,
                        support_contact=support_contact,
                    )
                else:
                    msg_text = (
                        f"⏳ Order #{order.id} — Under Review\n\n"
                        "Your payment was received but requires manual verification.\n"
                        f"Our team will review it shortly. Contact {support_contact} for help."
                    )

                telegram_id = order.telegram_user.telegram_id

            await session.commit()
            await _send_telegram_message(telegram_id, msg_text)

        elif status == "wrong_amount":
            order.status = OrderStatus.manual_review
            await session.commit()

        else:
            # Other statuses: log only
            logger.info(
                "Cryptomus webhook: unhandled status=%s for order=%s",
                status,
                order.id,
            )

        # Mark event as processed
        ev = await session.get(WebhookEvent, event_id)
        if ev:
            ev.processed = True
            await session.commit()

    return Response(status_code=200, content="ok")
