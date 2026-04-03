from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 New Order", callback_data="new_order")]
        ]
    )


def countries_keyboard(countries: list) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=c.prefix, callback_data=f"country:{c.id}")
        for c in countries
    ]
    rows = [buttons[i : i + 4] for i in range(0, len(buttons), 4)]
    rows.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def states_keyboard(states: list) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=s.name, callback_data=f"state:{s.id}")
        for s in states
    ]
    rows = [[b] for b in buttons]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_country")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plans_keyboard(plans: list, country_prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for p in plans:
        label = (
            f"{country_prefix}-{p.name}\n"
            f"{p.ram_gb}GB Ram | {p.cpu_cores} Core CPU | {p.ssd_gb}GB SSD\n"
            f"${float(p.price_usd):.2f}"
        )
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"plan:{p.id}")]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_state_or_country")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def os_keyboard(os_options: list) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=o.name, callback_data=f"os:{o.id}")
        for o in os_options
    ]
    rows = [[b] for b in buttons]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_plan")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def validity_keyboard(validities: list) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=v.label, callback_data=f"validity:{v.id}")
        for v in validities
    ]
    rows = [[b] for b in buttons]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_os")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def email_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_validity")]
        ]
    )


def payment_keyboard(pay_url: str, has_invoice: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="💳 Pay Now", url=pay_url)],
        [InlineKeyboardButton(text="I Paid ✅", callback_data="i_paid")],
    ]
    if not has_invoice:
        rows.append(
            [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_email")]
        )
    else:
        rows.append(
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
