from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import AsyncSessionLocal
from models.order import Order, OrderStatus, Payment, PaymentStatus

logger = logging.getLogger(__name__)


async def expire_pending_payments() -> None:
    """Expire orders that have passed their payment deadline."""
    now = datetime.now(timezone.utc)
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Payment)
                .join(Order, Payment.order_id == Order.id)
                .where(
                    Payment.status == PaymentStatus.pending,
                    Order.status == OrderStatus.pending_payment,
                    Payment.expires_at < now,
                )
                .options(selectinload(Payment.order))
            )
            payments = result.scalars().all()

            for payment in payments:
                order = payment.order
                payment.status = PaymentStatus.expired
                order.status = OrderStatus.cancelled_expired
                logger.info(
                    "Expired payment for order #%s (expires_at=%s)",
                    order.id,
                    payment.expires_at,
                )

            if payments:
                await session.commit()

    except Exception as exc:
        logger.error("Error in expire_pending_payments: %s", exc)


async def run_scheduler() -> None:
    """Run the payment expiry scheduler in the background every 60 seconds."""
    logger.info("Payment expiry scheduler started")
    while True:
        await expire_pending_payments()
        await asyncio.sleep(60)
