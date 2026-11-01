from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ContactForm(StatesGroup):
    name = State()
    date = State()
    year = State()
    relation = State()
    target = State()
    tg_id = State()
    confirm = State()


class EditContact(StatesGroup):
    name = State()
    date = State()
    tg_id = State()


class AnniversaryForm(StatesGroup):
    title = State()
    date = State()
    kind = State()
    start_year = State()
    recurring = State()
    target = State()
    confirm = State()


class EditAnniversary(StatesGroup):
    title = State()
    date = State()


class SettingsForm(StatesGroup):
    digest_time = State()
