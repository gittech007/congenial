from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class OrderStatus(str, enum.Enum):
    pending_payment = "pending_payment"
    processing = "processing"
    completed = "completed"
    cancelled_expired = "cancelled_expired"
    manual_review = "manual_review"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid_on_time = "paid_on_time"
    paid_late = "paid_late"
    expired = "expired"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        server_default="nextval('order_id_seq')",
    )
    telegram_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_users.id"), nullable=False
    )
    country_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("countries.id"), nullable=False
    )
    us_state_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("us_states.id"), nullable=True
    )
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plans.id"), nullable=False
    )
    os_option_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("os_options.id"), nullable=False
    )
    validity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validities.id"), nullable=False
    )
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), nullable=False, default=OrderStatus.pending_payment
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    telegram_user: Mapped["TelegramUser"] = relationship("TelegramUser", back_populates="orders")
    country: Mapped["Country"] = relationship("Country", back_populates="orders")
    us_state: Mapped["USState | None"] = relationship("USState", back_populates="orders")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="orders")
    os_option: Mapped["OSOption"] = relationship("OSOption", back_populates="orders")
    validity: Mapped["Validity"] = relationship("Validity", back_populates="orders")
    payment: Mapped[Payment | None] = relationship(
        "Payment", back_populates="order", uselist=False
    )
    delivery: Mapped[Delivery | None] = relationship(
        "Delivery", back_populates="order", uselist=False
    )

    def __str__(self) -> str:
        return f"Order #{self.id}"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False, unique=True
    )
    cryptomus_invoice_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    amount_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    order: Mapped[Order] = relationship("Order", back_populates="payment")

    def __str__(self) -> str:
        return f"Payment for Order #{self.order_id}"


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False
    )
    ip_address: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    expiry_date: Mapped[str] = mapped_column(String(20), nullable=False)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped[Order] = relationship("Order", back_populates="delivery")

    def __str__(self) -> str:
        return f"Delivery for Order #{self.order_id}"
