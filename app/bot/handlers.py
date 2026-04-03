from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot.keyboards import (
    countries_keyboard,
    email_back_keyboard,
    main_menu_keyboard,
    os_keyboard,
    payment_keyboard,
    plans_keyboard,
    states_keyboard,
    validity_keyboard,
)
from bot.utils import (
    get_message_template,
    get_or_create_user,
    get_or_create_user_state,
    get_setting,
    is_valid_email,
    save_user_state,
)
from database import AsyncSessionLocal
from models.catalog import Country, OSOption, Plan, USState, Validity
from models.config import Setting
from models.order import Order, OrderStatus, Payment, PaymentStatus
from models.telegram import UserState
from payments.cryptomus import create_invoice

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────── helpers ─────────────────────────────────────

async def _send_welcome(message: Message) -> None:
    tmpl = await get_message_template("welcome")
    text = tmpl or (
        "👋 Welcome to RDP Aura Bot!\n"
        "Purchase premium RDP access with crypto payments.\n"
        "Click below to start your order."
    )
    await message.answer(text, reply_markup=main_menu_keyboard())


async def _show_countries(message_or_query, user_db_id: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Country).where(Country.is_active.is_(True)).order_by(Country.sort_order)
        )
        countries = result.scalars().all()

    # Check maintenance mode
    maintenance = await get_setting("maintenance_mode")
    if maintenance and maintenance.lower() == "true":
        text = "🔧 The bot is currently under maintenance. Please try again later."
        if isinstance(message_or_query, CallbackQuery):
            await message_or_query.message.edit_text(text)
        else:
            await message_or_query.answer(text)
        return

    text = "🌍 Select your country:"
    kb = countries_keyboard(countries)
    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.message.edit_text(text, reply_markup=kb)
    else:
        await message_or_query.answer(text, reply_markup=kb)


# ──────────────────────────────── /start ─────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    from_ = message.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)
    # Reset state on /start
    state.current_step = "welcome"
    state.selected_country_id = None
    state.selected_state_id = None
    state.selected_plan_id = None
    state.selected_os_id = None
    state.selected_validity_id = None
    state.customer_email = None
    state.current_order_id = None
    await save_user_state(state)
    await _send_welcome(message)


# ─────────────────────────────── main menu ───────────────────────────────────

@router.callback_query(F.data == "new_order")
async def cb_new_order(query: CallbackQuery) -> None:
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)
    state.current_step = "country"
    state.selected_country_id = None
    state.selected_state_id = None
    state.selected_plan_id = None
    state.selected_os_id = None
    state.selected_validity_id = None
    state.customer_email = None
    state.current_order_id = None
    await save_user_state(state)
    await _show_countries(query, user.id)
    await query.answer()


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(query: CallbackQuery) -> None:
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)
    state.current_step = "welcome"
    await save_user_state(state)
    tmpl = await get_message_template("welcome")
    text = tmpl or (
        "👋 Welcome to RDP Aura Bot!\n"
        "Purchase premium RDP access with crypto payments.\n"
        "Click below to start your order."
    )
    await query.message.edit_text(text, reply_markup=main_menu_keyboard())
    await query.answer()


# ──────────────────────────── country selection ───────────────────────────────

@router.callback_query(F.data.startswith("country:"))
async def cb_country(query: CallbackQuery) -> None:
    country_id = int(query.data.split(":")[1])
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)

    # If country changed, clear downstream selections
    if state.selected_country_id != country_id:
        state.selected_state_id = None
        state.selected_plan_id = None
        state.selected_os_id = None
        state.selected_validity_id = None
        state.customer_email = None
        state.current_order_id = None

    state.selected_country_id = country_id
    state.current_step = "country"
    await save_user_state(state)

    async with AsyncSessionLocal() as session:
        country = await session.get(Country, country_id)

    # Check if US → show states
    if country and country.prefix == "US":
        state.current_step = "state_selection"
        await save_user_state(state)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(USState)
                .where(USState.country_id == country_id, USState.is_active.is_(True))
                .order_by(USState.sort_order)
            )
            states = result.scalars().all()
        await query.message.edit_text(
            "🗺️ Select your US state:", reply_markup=states_keyboard(states)
        )
    else:
        await _show_plans(query, state, country)

    await query.answer()


# ─────────────────────────────── state selection ─────────────────────────────

@router.callback_query(F.data.startswith("state:"))
async def cb_state(query: CallbackQuery) -> None:
    state_id = int(query.data.split(":")[1])
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)

    if state.selected_state_id != state_id:
        state.selected_plan_id = None
        state.selected_os_id = None
        state.selected_validity_id = None
        state.customer_email = None
        state.current_order_id = None

    state.selected_state_id = state_id
    state.current_step = "state_selection"
    await save_user_state(state)

    async with AsyncSessionLocal() as session:
        country = await session.get(Country, state.selected_country_id)

    await _show_plans(query, state, country)
    await query.answer()


# ─────────────────────────────── plan helpers ────────────────────────────────

async def _show_plans(query: CallbackQuery, user_state: UserState, country) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order)
        )
        plans = result.scalars().all()

    prefix = country.prefix if country else "RDP"
    await query.message.edit_text(
        "📦 Select your plan:", reply_markup=plans_keyboard(plans, prefix)
    )


# ─────────────────────────────── plan selection ──────────────────────────────

@router.callback_query(F.data.startswith("plan:"))
async def cb_plan(query: CallbackQuery) -> None:
    plan_id = int(query.data.split(":")[1])
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)

    if state.selected_plan_id != plan_id:
        state.selected_os_id = None
        state.selected_validity_id = None
        state.customer_email = None
        state.current_order_id = None

    state.selected_plan_id = plan_id
    state.current_step = "plan"
    await save_user_state(state)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(OSOption).where(OSOption.is_active.is_(True)).order_by(OSOption.sort_order)
        )
        os_options = result.scalars().all()

    await query.message.edit_text(
        "💻 Select your OS:", reply_markup=os_keyboard(os_options)
    )
    await query.answer()


# ─────────────────────────────── OS selection ────────────────────────────────

@router.callback_query(F.data.startswith("os:"))
async def cb_os(query: CallbackQuery) -> None:
    os_id = int(query.data.split(":")[1])
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)

    if state.selected_os_id != os_id:
        state.selected_validity_id = None
        state.customer_email = None
        state.current_order_id = None

    state.selected_os_id = os_id
    state.current_step = "os"
    await save_user_state(state)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Validity).where(Validity.is_active.is_(True))
        )
        validities = result.scalars().all()

    await query.message.edit_text(
        "📅 Select validity period:", reply_markup=validity_keyboard(validities)
    )
    await query.answer()


# ─────────────────────────────── validity selection ──────────────────────────

@router.callback_query(F.data.startswith("validity:"))
async def cb_validity(query: CallbackQuery) -> None:
    validity_id = int(query.data.split(":")[1])
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)

    if state.selected_validity_id != validity_id:
        state.customer_email = None
        state.current_order_id = None

    state.selected_validity_id = validity_id
    state.current_step = "validity"
    await save_user_state(state)

    await query.message.edit_text(
        "📧 Please enter your email address:",
        reply_markup=email_back_keyboard(),
    )
    await query.answer()


# ─────────────────────────────── email collection ────────────────────────────

@router.message(F.text)
async def handle_text(message: Message) -> None:
    from_ = message.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)

    if state.current_step != "validity":
        # Not expecting email; ignore or show help
        await _send_welcome(message)
        return

    email = message.text.strip()
    if not is_valid_email(email):
        await message.answer(
            "❌ Invalid email address. Please enter a valid email:",
            reply_markup=email_back_keyboard(),
        )
        return

    state.customer_email = email
    state.current_step = "email"
    await save_user_state(state)

    # Build order summary and create Cryptomus invoice
    await _proceed_to_payment(message, state, user)


async def _proceed_to_payment(message: Message, user_state: UserState, user) -> None:
    async with AsyncSessionLocal() as session:
        country = await session.get(Country, user_state.selected_country_id)
        us_state = (
            await session.get(USState, user_state.selected_state_id)
            if user_state.selected_state_id
            else None
        )
        plan = await session.get(Plan, user_state.selected_plan_id)
        os_opt = await session.get(OSOption, user_state.selected_os_id)
        validity = await session.get(Validity, user_state.selected_validity_id)

    if not all([country, plan, os_opt, validity]):
        await message.answer("⚠️ Session data missing. Please start over.", reply_markup=main_menu_keyboard())
        return

    price = float(plan.price_usd)

    # Fetch order summary template
    tmpl = await get_message_template("order_summary")
    state_name = us_state.name if us_state else "—"
    if tmpl:
        summary_text = tmpl.format(
            country=country.name,
            state=state_name,
            plan=f"{country.prefix}-{plan.name}",
            os=os_opt.name,
            validity=validity.label,
            email=user_state.customer_email,
            price=f"{price:.2f}",
            order_id="(pending)",
        )
    else:
        summary_text = (
            f"📋 Order Summary\n\n"
            f"🌍 Country: {country.name}\n"
            f"🗺️ State: {state_name}\n"
            f"📦 Plan: {country.prefix}-{plan.name}\n"
            f"💻 OS: {os_opt.name}\n"
            f"📅 Validity: {validity.label}\n"
            f"📧 Email: {user_state.customer_email}\n"
            f"💰 Price: ${price:.2f}"
        )

    # Create Order record
    async with AsyncSessionLocal() as session:
        order = Order(
            telegram_user_id=user.id,
            country_id=country.id,
            us_state_id=us_state.id if us_state else None,
            plan_id=plan.id,
            os_option_id=os_opt.id,
            validity_id=validity.id,
            customer_email=user_state.customer_email,
            status=OrderStatus.pending_payment,
        )
        session.add(order)
        await session.flush()  # Get order.id

        # Create Payment record with expires_at
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        payment = Payment(
            order_id=order.id,
            amount_usd=price,
            status=PaymentStatus.pending,
            expires_at=expires_at,
        )
        session.add(payment)
        await session.commit()
        await session.refresh(order)
        order_id = order.id

    # Create Cryptomus invoice
    try:
        invoice = await create_invoice(order_id=order_id, amount_usd=price)
        pay_url = invoice.get("url") or invoice.get("payment_url", "")
        invoice_uuid = invoice.get("uuid", "")

        async with AsyncSessionLocal() as session:
            pymt = await session.execute(
                select(Payment).where(Payment.order_id == order_id)
            )
            pymt_obj = pymt.scalar_one()
            pymt_obj.cryptomus_invoice_id = invoice_uuid
            await session.commit()

        # Update user state with order
        user_state.current_order_id = order_id
        user_state.current_step = "payment"
        await save_user_state(user_state)

        payment_tmpl = await get_message_template("payment_created")
        if payment_tmpl:
            pay_text = payment_tmpl.format(order_id=order_id, amount=f"{price:.2f}")
        else:
            pay_text = (
                f"💳 Invoice created for Order #{order_id}\n\n"
                f"Amount: ${price:.2f} USD\n"
                "Expires in 2 hours.\n\n"
                "Click the Pay Now button below to complete your payment."
            )

        full_text = summary_text + "\n\n" + pay_text
        await message.answer(
            full_text,
            reply_markup=payment_keyboard(pay_url, has_invoice=True),
        )

    except Exception as exc:
        logger.error("Failed to create Cryptomus invoice for order %s: %s", order_id, exc)
        await message.answer(
            f"⚠️ Could not create payment invoice. Please contact support.\n\nOrder #{order_id} has been created.",
            reply_markup=main_menu_keyboard(),
        )


# ─────────────────────────────── "I Paid" ────────────────────────────────────

@router.callback_query(F.data == "i_paid")
async def cb_i_paid(query: CallbackQuery) -> None:
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)

    if not state.current_order_id:
        await query.answer("No active order found.", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Payment).where(Payment.order_id == state.current_order_id)
        )
        payment = result.scalar_one_or_none()

    if payment and payment.status == PaymentStatus.paid_on_time:
        await query.answer("✅ Your payment has been confirmed!", show_alert=True)
    elif payment and payment.status == PaymentStatus.expired:
        await query.answer("❌ Your invoice has expired. Please start a new order.", show_alert=True)
        await query.message.edit_reply_markup(reply_markup=main_menu_keyboard())
    else:
        await query.answer(
            "⏳ We haven't received your payment yet. Please complete payment and try again.",
            show_alert=True,
        )


# ──────────────────────────────── back buttons ───────────────────────────────

@router.callback_query(F.data == "back_to_country")
async def cb_back_to_country(query: CallbackQuery) -> None:
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)
    state.current_step = "country"
    await save_user_state(state)
    await _show_countries(query, user.id)
    await query.answer()


@router.callback_query(F.data == "back_to_state_or_country")
async def cb_back_to_state_or_country(query: CallbackQuery) -> None:
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)

    async with AsyncSessionLocal() as session:
        country = await session.get(Country, state.selected_country_id)

    if country and country.prefix == "US":
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(USState)
                .where(USState.country_id == country.id, USState.is_active.is_(True))
                .order_by(USState.sort_order)
            )
            states = result.scalars().all()
        state.current_step = "state_selection"
        await save_user_state(state)
        await query.message.edit_text(
            "🗺️ Select your US state:", reply_markup=states_keyboard(states)
        )
    else:
        state.current_step = "country"
        await save_user_state(state)
        await _show_countries(query, user.id)

    await query.answer()


@router.callback_query(F.data == "back_to_plan")
async def cb_back_to_plan(query: CallbackQuery) -> None:
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)

    async with AsyncSessionLocal() as session:
        country = await session.get(Country, state.selected_country_id)
        result = await session.execute(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order)
        )
        plans = result.scalars().all()

    prefix = country.prefix if country else "RDP"
    state.current_step = "plan"
    await save_user_state(state)
    await query.message.edit_text(
        "📦 Select your plan:", reply_markup=plans_keyboard(plans, prefix)
    )
    await query.answer()


@router.callback_query(F.data == "back_to_os")
async def cb_back_to_os(query: CallbackQuery) -> None:
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)
    state.current_step = "os"
    await save_user_state(state)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(OSOption).where(OSOption.is_active.is_(True)).order_by(OSOption.sort_order)
        )
        os_options = result.scalars().all()

    await query.message.edit_text(
        "💻 Select your OS:", reply_markup=os_keyboard(os_options)
    )
    await query.answer()


@router.callback_query(F.data == "back_to_validity")
async def cb_back_to_validity(query: CallbackQuery) -> None:
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)
    state.current_step = "os"
    await save_user_state(state)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Validity).where(Validity.is_active.is_(True))
        )
        validities = result.scalars().all()

    await query.message.edit_text(
        "📅 Select validity period:", reply_markup=validity_keyboard(validities)
    )
    await query.answer()


@router.callback_query(F.data == "back_to_email")
async def cb_back_to_email(query: CallbackQuery) -> None:
    from_ = query.from_user
    user = await get_or_create_user(
        telegram_id=from_.id,
        first_name=from_.first_name,
        last_name=from_.last_name,
        username=from_.username,
    )
    state = await get_or_create_user_state(user.id)
    state.current_step = "validity"
    state.customer_email = None
    state.current_order_id = None
    await save_user_state(state)

    await query.message.edit_text(
        "📧 Please enter your email address:",
        reply_markup=email_back_keyboard(),
    )
    await query.answer()
