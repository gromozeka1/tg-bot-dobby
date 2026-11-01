from __future__ import annotations

from collections.abc import Callable

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.bot.keyboards import main_menu, menu_kb
from dobby.db.models import User
from dobby.services.accounts import delete_account

router = Router(name="common")
T = Callable[..., str]


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, _: T) -> None:
    await state.clear()
    await message.answer(_("Cancelled."), reply_markup=main_menu(_))


@router.message(Command("help"))
async def cmd_help(message: Message, _: T) -> None:
    await message.answer(
        _(
            "I can remember birthdays and anniversaries and congratulate people.\n\n"
            "/today — what is today\n"
            "/upcoming — the next 14 days\n"
            "/contacts — contact list\n"
            "/addcontact — add a contact\n"
            "/anniversaries — anniversary list\n"
            "/addanniversary — add an anniversary\n"
            "/subscriptions — what goes into the digest and the group\n"
            "/settings — time, reminders, language\n"
            "/bindgroup — bind this group (send it in the group)\n"
            "/delete_me — permanently delete your data\n"
            "/cancel — cancel the current step"
        ),
        reply_markup=main_menu(_),
    )


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    if message.from_user is None:
        return
    text = f"ID: <code>{message.from_user.id}</code>"
    if message.chat.id != message.from_user.id:
        text += f"\nChat ID: <code>{message.chat.id}</code>"
    await message.answer(text, parse_mode="HTML")


@router.message(Command("delete_me"))
async def cmd_delete_me(message: Message, _: T) -> None:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=_("🗑 Delete my data"), callback_data="account:delete:yes"),
        InlineKeyboardButton(text=_("❌ Cancel"), callback_data="account:delete:no"),
    )
    await message.answer(
        _("This permanently deletes your account and all saved data. Continue?"),
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("account:delete:"))
async def cb_delete_me(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User,
    state: FSMContext,
    _: T,
) -> None:
    action = (callback.data or "").rsplit(":", 1)[-1]
    if action == "yes":
        await delete_account(session, db_user.id)
        await state.clear()
        await callback.answer(_("Deleted."))
        if callback.message is not None:
            await callback.message.edit_text(_("Your account and saved data were deleted."))
        return
    await callback.answer(_("Cancelled."))
    if callback.message is not None:
        await callback.message.edit_text(_("Cancelled."))


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, _: T) -> None:
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(_("🏠 Main menu"), reply_markup=menu_kb(_))
        await callback.message.answer(_("Choose an action:"), reply_markup=main_menu(_))


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery, _: T) -> None:
    await callback.answer(_("Nothing to do here."))


@router.callback_query(F.data == "set:bindhint")
async def cb_bind_hint(callback: CallbackQuery, _: T) -> None:
    await callback.answer(
        _(
            "Add me to the group, make me an administrator (or allow messages), "
            "then send /bindgroup in that group."
        ),
        show_alert=True,
    )
