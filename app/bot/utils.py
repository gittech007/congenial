from __future__ import annotations

import logging
import re

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import AsyncSessionLocal
from models.config import MessageTemplate, Setting
from models.telegram import TelegramUser, UserState

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


async def get_or_create_user(telegram_id: int, first_name: str | None, last_name: str | None, username: str | None) -> TelegramUser:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = TelegramUser(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Update profile fields
            changed = False
            if user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if user.last_name != last_name:
                user.last_name = last_name
                changed = True
            if user.username != username:
                user.username = username
                changed = True
            if changed:
                await session.commit()
                await session.refresh(user)
        return user


async def get_user_state(telegram_user_id: int) -> UserState | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserState).where(UserState.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()


async def save_user_state(state: UserState) -> None:
    async with AsyncSessionLocal() as session:
        # Merge the detached instance
        merged = await session.merge(state)
        await session.commit()


async def get_or_create_user_state(telegram_user_id: int) -> UserState:
    existing = await get_user_state(telegram_user_id)
    if existing:
        return existing
    async with AsyncSessionLocal() as session:
        new_state = UserState(telegram_user_id=telegram_user_id)
        session.add(new_state)
        await session.commit()
        await session.refresh(new_state)
        return new_state


async def get_setting(key: str) -> str | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else None


async def get_message_template(slug: str) -> str | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MessageTemplate).where(MessageTemplate.slug == slug)
        )
        tmpl = result.scalar_one_or_none()
        return tmpl.body_text if tmpl else None


async def send_message_to_user(telegram_id: int, text: str, **kwargs) -> None:
    """Send a message to a Telegram user by telegram_id."""
    from main import bot_instance
    if bot_instance is None:
        logger.error("Bot instance not available, cannot send message to %s", telegram_id)
        return
    try:
        await bot_instance.send_message(chat_id=telegram_id, text=text, **kwargs)
    except Exception as exc:
        logger.error("Failed to send message to %s: %s", telegram_id, exc)
