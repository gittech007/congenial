from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://rdpaura:changeme@postgres:5432/rdpaura"
    postgres_user: str = "rdpaura"
    postgres_password: str = "changeme"
    postgres_db: str = "rdpaura"

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = "asdfg"
    telegram_webhook_url: str = "https://panel.rdpaura.me/telegram/webhook/asdfg"

    # Cryptomus
    cryptomus_api_key: str = ""
    cryptomus_merchant_id: str = ""

    # Admin
    admin_username: str = "admin"
    admin_password: str = "changeme_admin_password"
    admin_secret_key: str = "changeme_secret_key_for_sessions"

    # App
    app_domain: str = "panel.rdpaura.me"
    debug: bool = False


settings = Settings()
