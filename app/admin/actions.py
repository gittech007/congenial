from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqladmin import action
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from admin.views import OrderAdmin
from bot.utils import get_message_template, get_setting, send_message_to_user
from database import AsyncSessionLocal
from models.order import Delivery, Order, OrderStatus, Payment
from models.telegram import TelegramUser
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class OrderAdminWithActions(OrderAdmin):
    """Extends OrderAdmin with custom admin actions."""

    @action(
        name="approve_late_payment",
        label="✅ Approve Late Payment",
        confirmation_message="Approve late payment and set status to Processing?",
        add_in_detail=True,
        add_in_list=True,
    )
    async def approve_late_payment(self, request: Request) -> Response:
        pks = request.query_params.getlist("pks")
        if not pks:
            pk = request.path_params.get("pk")
            if pk:
                pks = [pk]

        for pk in pks:
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Order)
                        .where(Order.id == int(pk))
                        .options(selectinload(Order.telegram_user))
                    )
                    order = result.scalar_one_or_none()
                    if not order or order.status != OrderStatus.manual_review:
                        continue

                    order.status = OrderStatus.processing

                    # Fetch fulfillment ETA
                    from models.config import Setting, MessageTemplate
                    eta_row = await session.execute(
                        select(Setting).where(Setting.key == "fulfillment_eta")
                    )
                    eta_setting = eta_row.scalar_one_or_none()
                    fulfillment_eta = eta_setting.value if eta_setting else "Completed within 1–4 hours"

                    tmpl_row = await session.execute(
                        select(MessageTemplate).where(MessageTemplate.slug == "processing")
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
                    await session.commit()

                await send_message_to_user(telegram_id, msg_text)

            except Exception as exc:
                logger.error("approve_late_payment error for pk=%s: %s", pk, exc)

        return RedirectResponse(request.url_for("admin:list", identity="order"), status_code=302)

    @action(
        name="reject_late_payment",
        label="❌ Reject Late Payment",
        confirmation_message="Reject late payment and cancel the order?",
        add_in_detail=True,
        add_in_list=True,
    )
    async def reject_late_payment(self, request: Request) -> Response:
        pks = request.query_params.getlist("pks")
        if not pks:
            pk = request.path_params.get("pk")
            if pk:
                pks = [pk]

        for pk in pks:
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Order)
                        .where(Order.id == int(pk))
                        .options(selectinload(Order.telegram_user))
                    )
                    order = result.scalar_one_or_none()
                    if not order or order.status != OrderStatus.manual_review:
                        continue

                    order.status = OrderStatus.cancelled_expired
                    telegram_id = order.telegram_user.telegram_id
                    order_id = order.id
                    await session.commit()

                # Optionally notify user
                await send_message_to_user(
                    telegram_id,
                    f"❌ Order #{order_id} has been cancelled after manual review.",
                )

            except Exception as exc:
                logger.error("reject_late_payment error for pk=%s: %s", pk, exc)

        return RedirectResponse(request.url_for("admin:list", identity="order"), status_code=302)

    @action(
        name="mark_completed",
        label="🎉 Mark Completed + Send Delivery",
        confirmation_message=None,
        add_in_detail=True,
        add_in_list=True,
    )
    async def mark_completed(self, request: Request) -> Response:
        if request.method == "GET":
            pks = request.query_params.getlist("pks")
            pk = request.path_params.get("pk")
            pks_str = "&".join(f"pks={p}" for p in (pks or ([pk] if pk else [])))
            # Return a simple form for IP/USER/PASS/Expiry
            html = f"""
<!DOCTYPE html><html><head><title>Mark Completed</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head><body class="p-4">
<h3>Mark Order Completed</h3>
<form method="post">
<input type="hidden" name="pks_raw" value="{",".join(pks or ([pk] if pk else []))}">
<div class="mb-3"><label class="form-label">IP Address</label><input class="form-control" name="ip_address" required></div>
<div class="mb-3"><label class="form-label">Username</label><input class="form-control" name="username" required></div>
<div class="mb-3"><label class="form-label">Password</label><input class="form-control" name="password" required></div>
<div class="mb-3"><label class="form-label">Expiry Date (YYYY-MM-DD)</label><input class="form-control" name="expiry_date" required pattern="\\d{{4}}-\\d{{2}}-\\d{{2}}"></div>
<button type="submit" class="btn btn-success">Mark Completed & Send</button>
<a href="javascript:history.back()" class="btn btn-secondary ms-2">Cancel</a>
</form></body></html>
"""
            return Response(content=html, media_type="text/html")

        form = await request.form()
        ip_address = form.get("ip_address", "")
        username = form.get("username", "")
        password = form.get("password", "")
        expiry_date = form.get("expiry_date", "")
        pks_raw = form.get("pks_raw", "")
        pks = [p.strip() for p in pks_raw.split(",") if p.strip()]

        for pk in pks:
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Order)
                        .where(Order.id == int(pk))
                        .options(selectinload(Order.telegram_user))
                    )
                    order = result.scalar_one_or_none()
                    if not order or order.status != OrderStatus.processing:
                        continue

                    delivery = Delivery(
                        order_id=order.id,
                        ip_address=ip_address,
                        username=username,
                        password=password,
                        expiry_date=expiry_date,
                    )
                    session.add(delivery)
                    order.status = OrderStatus.completed
                    telegram_id = order.telegram_user.telegram_id
                    order_id = order.id
                    await session.commit()

                from models.config import MessageTemplate
                async with AsyncSessionLocal() as session:
                    tmpl_row = await session.execute(
                        select(MessageTemplate).where(MessageTemplate.slug == "completed")
                    )
                    tmpl = tmpl_row.scalar_one_or_none()

                if tmpl:
                    msg_text = tmpl.body_text.format(
                        order_id=order_id,
                        ip=ip_address,
                        username=username,
                        password=password,
                        expiry_date=expiry_date,
                    )
                else:
                    msg_text = (
                        f"🎉 Order #{order_id} — Completed!\n\n"
                        f"Your RDP Access Details:\n"
                        f"🌐 IP: {ip_address}\n"
                        f"👤 User: {username}\n"
                        f"🔑 Pass: {password}\n"
                        f"📅 Expires: {expiry_date}\n\n"
                        "Save these credentials securely!"
                    )

                await send_message_to_user(telegram_id, msg_text)

            except Exception as exc:
                logger.error("mark_completed error for pk=%s: %s", pk, exc)

        return RedirectResponse(request.url_for("admin:list", identity="order"), status_code=302)

    @action(
        name="resend_delivery",
        label="🔄 Resend Delivery",
        confirmation_message="Resend delivery credentials to the customer?",
        add_in_detail=True,
        add_in_list=True,
    )
    async def resend_delivery(self, request: Request) -> Response:
        pks = request.query_params.getlist("pks")
        if not pks:
            pk = request.path_params.get("pk")
            if pk:
                pks = [pk]

        for pk in pks:
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Order)
                        .where(Order.id == int(pk))
                        .options(
                            selectinload(Order.telegram_user),
                            selectinload(Order.delivery),
                        )
                    )
                    order = result.scalar_one_or_none()
                    if not order or order.status != OrderStatus.completed:
                        continue
                    if not order.delivery:
                        continue

                    delivery = order.delivery
                    telegram_id = order.telegram_user.telegram_id
                    order_id = order.id

                from models.config import MessageTemplate
                async with AsyncSessionLocal() as session:
                    tmpl_row = await session.execute(
                        select(MessageTemplate).where(MessageTemplate.slug == "completed")
                    )
                    tmpl = tmpl_row.scalar_one_or_none()

                if tmpl:
                    msg_text = tmpl.body_text.format(
                        order_id=order_id,
                        ip=delivery.ip_address,
                        username=delivery.username,
                        password=delivery.password,
                        expiry_date=delivery.expiry_date,
                    )
                else:
                    msg_text = (
                        f"🎉 Order #{order_id} — Completed!\n\n"
                        f"Your RDP Access Details:\n"
                        f"🌐 IP: {delivery.ip_address}\n"
                        f"👤 User: {delivery.username}\n"
                        f"🔑 Pass: {delivery.password}\n"
                        f"📅 Expires: {delivery.expiry_date}\n\n"
                        "Save these credentials securely!"
                    )

                await send_message_to_user(telegram_id, msg_text)

            except Exception as exc:
                logger.error("resend_delivery error for pk=%s: %s", pk, exc)

        return RedirectResponse(request.url_for("admin:list", identity="order"), status_code=302)
