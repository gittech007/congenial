from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware

from admin.actions import OrderAdminWithActions
from admin.auth import AdminAuth
from admin.views import (
    CountryAdmin,
    DeliveryAdmin,
    MessageTemplateAdmin,
    OSOptionAdmin,
    PaymentAdmin,
    PlanAdmin,
    SettingAdmin,
    TelegramUserAdmin,
    USStateAdmin,
    ValidityAdmin,
    WebhookEventAdmin,
)
from bot.handlers import router as bot_router
from config import settings
from database import engine
from payments.webhook import router as payments_router
from routes import router as telegram_router
from scheduler import run_scheduler

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Global bot / dispatcher instances (set during lifespan)
bot_instance: Bot | None = None
dp_instance: Dispatcher | None = None
_scheduler_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_instance, dp_instance, _scheduler_task

    # ── Bot setup ──────────────────────────────────────────────────────────
    bot_instance = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp_instance = Dispatcher()
    dp_instance.include_router(bot_router)

    # Set Telegram webhook
    webhook_url = settings.telegram_webhook_url
    try:
        await bot_instance.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
        )
        logger.info("Telegram webhook set to: %s", webhook_url)
    except Exception as exc:
        logger.error("Failed to set Telegram webhook: %s", exc)

    # ── Start scheduler ────────────────────────────────────────────────────
    _scheduler_task = asyncio.create_task(run_scheduler())
    logger.info("Payment expiry scheduler started")

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass

    try:
        await bot_instance.delete_webhook()
    except Exception:
        pass
    await bot_instance.session.close()
    await engine.dispose()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="RDP Aura Bot",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)

# Session middleware (required for SQLAdmin auth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.admin_secret_key,
)

# ── Admin panel ────────────────────────────────────────────────────────────
authentication_backend = AdminAuth(secret_key=settings.admin_secret_key)
admin = Admin(
    app=app,
    engine=engine,
    authentication_backend=authentication_backend,
    title="RDP Aura Admin",
    base_url="/admin",
)

admin.add_view(CountryAdmin)
admin.add_view(USStateAdmin)
admin.add_view(PlanAdmin)
admin.add_view(OSOptionAdmin)
admin.add_view(ValidityAdmin)
admin.add_view(OrderAdminWithActions)
admin.add_view(PaymentAdmin)
admin.add_view(DeliveryAdmin)
admin.add_view(SettingAdmin)
admin.add_view(MessageTemplateAdmin)
admin.add_view(TelegramUserAdmin)
admin.add_view(WebhookEventAdmin)

# ── Routes ─────────────────────────────────────────────────────────────────
app.include_router(telegram_router)
app.include_router(payments_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
