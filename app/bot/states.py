from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class OrderFlow(StatesGroup):
    country = State()
    state_selection = State()
    plan = State()
    os = State()
    validity = State()
    email = State()
    payment = State()
