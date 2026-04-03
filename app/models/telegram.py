from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class TelegramUser(Base):
    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    first_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    username: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="telegram_user")
    state: Mapped[UserState | None] = relationship(
        "UserState", back_populates="telegram_user", uselist=False
    )

    def __str__(self) -> str:
        return f"@{self.username}" if self.username else str(self.telegram_id)


class UserState(Base):
    __tablename__ = "user_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_users.id"), nullable=False, unique=True
    )
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selected_country_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_state_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_plan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_os_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_validity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_order_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    telegram_user: Mapped[TelegramUser] = relationship(
        "TelegramUser", back_populates="state"
    )

    def __str__(self) -> str:
        return f"State for user {self.telegram_user_id}"
