from __future__ import annotations

import logging

from aiogram.types import Update
from fastapi import APIRouter, Request, Response

from database import AsyncSessionLocal
from models.webhook import WebhookEvent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/telegram/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request) -> Response:
    from config import settings
    from main import bot_instance, dp_instance

    if secret != settings.telegram_webhook_secret:
        return Response(status_code=403, content="Forbidden")

    raw_body = await request.body()

    # Log the webhook event
    try:
        import json
        payload = json.loads(raw_body)
    except Exception:
        payload = None

    async with AsyncSessionLocal() as session:
        event = WebhookEvent(
            source="telegram",
            event_type="update",
            payload=payload,
            processed=False,
        )
        session.add(event)
        await session.commit()

    if dp_instance is None or bot_instance is None:
        logger.error("Bot or dispatcher not initialized")
        return Response(status_code=503, content="Service unavailable")

    try:
        update = Update.model_validate(payload)
        await dp_instance.feed_update(bot_instance, update)

        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(WebhookEvent).order_by(WebhookEvent.id.desc()).limit(1)
            )
            ev = result.scalar_one_or_none()
            if ev:
                ev.processed = True
                await session.commit()
    except Exception as exc:
        logger.error("Error processing Telegram update: %s", exc)

    return Response(status_code=200, content="ok")
