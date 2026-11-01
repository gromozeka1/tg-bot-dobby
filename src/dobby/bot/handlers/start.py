from __future__ import annotations

from collections.abc import Callable

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from dobby.bot.filters import MenuButton
from dobby.bot.keyboards import add_choice_kb, main_menu
from dobby.db.models import User

router = Router(name="start")
T = Callable[..., str]


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, _: T) -> None:
    name = db_user.first_name or (
        message.from_user.first_name if message.from_user else ""
    )
    if name:
        text = _(
            "👋 Hi, {name}! I'm Dobby.\n\n"
            "I remember birthdays and anniversaries, send you a morning digest "
            "and congratulate people in your family group."
        ).format(name=name)
    else:
        text = _(
            "👋 Hi! I'm Dobby.\n\n"
            "I remember birthdays and anniversaries, send you a morning digest "
            "and congratulate people in your family group."
        )
    await message.answer(text, reply_markup=main_menu(_))


@router.message(Command("menu"))
@router.message(MenuButton("🏠 Main menu"))
async def cmd_menu(message: Message, _: T) -> None:
    await message.answer(_("Choose an action:"), reply_markup=main_menu(_))


@router.message(MenuButton("➕ Add"))
async def cmd_add(message: Message, _: T) -> None:
    await message.answer(_("What do you want to add?"), reply_markup=add_choice_kb(_))


@router.callback_query(F.data == "add:contact")
async def cb_add_contact(callback: CallbackQuery, state: FSMContext, _: T) -> None:
    from dobby.bot.handlers.contacts import start_contact_form

    await start_contact_form(callback, state, _)


@router.callback_query(F.data == "add:anniversary")
async def cb_add_anniversary(callback: CallbackQuery, state: FSMContext, _: T) -> None:
    from dobby.bot.handlers.anniversaries import start_anniversary_form

    await start_anniversary_form(callback, state, _)
