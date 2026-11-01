from __future__ import annotations

import re
from collections.abc import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.bot.filters import MenuButton
from dobby.bot.keyboards import (
    language_kb,
    main_menu,
    reminder_kb,
    settings_kb,
    time_kb,
    timezone_kb,
)
from dobby.bot.states import SettingsForm
from dobby.db.models import Chat, User
from dobby.i18n import LOCALE_NAMES, get_translator

router = Router(name="settings")
T = Callable[..., str]
TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


async def _chat_count(session: AsyncSession, user: User) -> int:
    return int(
        await session.scalar(
            select(func.count(Chat.id)).where(Chat.owner_id == user.id)
        )
        or 0
    )


async def render_settings(
    message: Message,
    session: AsyncSession,
    user: User,
    _: T,
    *,
    edit: bool = True,
) -> None:
    count = await _chat_count(session, user)
    reminders = _("on") if user.reminders_enabled else _("off")
    text = "\n".join(
        [
            f"⚙️ <b>{_('Settings')}</b>",
            "",
            _("🕘 Digest time: {time}").format(time=user.digest_time),
            _("🌍 Time zone: {zone}").format(zone=user.timezone),
            _("⏰ Reminder: {state} ({days} d)").format(
                state=reminders, days=user.reminder_days_before
            ),
            _("📩 Digest: {state}").format(
                state=_("on") if user.dm_enabled else _("off")
            ),
            _("🎉 Group: {state}").format(
                state=_("on") if user.group_enabled else _("off")
            ),
            _("🌐 Language: {lang}").format(lang=LOCALE_NAMES.get(user.locale, user.locale)),
        ]
    )
    keyboard = settings_kb(user, count, _)
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.message(Command("settings"))
@router.message(MenuButton("⚙️ Settings"))
async def cmd_settings(
    message: Message, session: AsyncSession, db_user: User, _: T
) -> None:
    await render_settings(message, session, db_user, _, edit=False)


@router.callback_query(F.data == "set:menu")
async def cb_settings_menu(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    await callback.answer()
    if callback.message is not None:
        await render_settings(callback.message, session, db_user, _)


@router.callback_query(F.data == "set:time")
async def cb_time(
    callback: CallbackQuery, db_user: User, _: T
) -> None:
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(
            _("Choose the digest time:"), reply_markup=time_kb(db_user.digest_time, _)
        )


@router.callback_query(F.data.startswith("set:time:"))
async def cb_time_set(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    value = (callback.data or "").split(":", 2)[2]
    if not TIME_RE.match(value):
        await callback.answer(_("Invalid time."), show_alert=True)
        return
    db_user.digest_time = value
    await session.flush()
    await callback.answer(_("Saved."))
    if callback.message is not None:
        await render_settings(callback.message, session, db_user, _)


@router.callback_query(F.data == "set:timecustom")
async def cb_time_custom(
    callback: CallbackQuery, state: FSMContext, _: T
) -> None:
    await state.set_state(SettingsForm.digest_time)
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(_("Send the time in HH:MM format, for example 09:30."))


@router.message(SettingsForm.digest_time)
async def save_custom_time(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    value = (message.text or "").strip()
    if not TIME_RE.match(value):
        await message.answer(_("Invalid time. Send HH:MM, for example 09:30."))
        return
    db_user.digest_time = value.zfill(5)
    await session.flush()
    await state.clear()
    await message.answer(_("✅ Saved."))
    await render_settings(message, session, db_user, _, edit=False)


@router.callback_query(F.data == "set:tz")
async def cb_timezone(callback: CallbackQuery, db_user: User, _: T) -> None:
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(
            _("Choose the time zone:"), reply_markup=timezone_kb(db_user.timezone, _)
        )


@router.callback_query(F.data.startswith("set:tz:"))
async def cb_timezone_set(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    zone = (callback.data or "").split(":", 2)[2]
    try:
        ZoneInfo(zone)
    except ZoneInfoNotFoundError:
        await callback.answer(_("Unknown time zone."), show_alert=True)
        return
    db_user.timezone = zone
    await session.flush()
    await callback.answer(_("Saved."))
    if callback.message is not None:
        await render_settings(callback.message, session, db_user, _)


@router.callback_query(F.data == "set:rem")
async def cb_reminder(callback: CallbackQuery, db_user: User, _: T) -> None:
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(
            _("Reminder settings:"), reply_markup=reminder_kb(db_user, _)
        )


@router.callback_query(F.data == "set:remtoggle")
async def cb_reminder_toggle(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    db_user.reminders_enabled = not db_user.reminders_enabled
    await session.flush()
    await callback.answer(_("Saved."))
    if callback.message is not None:
        await callback.message.edit_text(
            _("Reminder settings:"), reply_markup=reminder_kb(db_user, _)
        )


@router.callback_query(F.data.startswith("set:remdays:"))
async def cb_reminder_days(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    days = int((callback.data or "").split(":")[2])
    if not 1 <= days <= 30:
        await callback.answer(_("Invalid value."), show_alert=True)
        return
    db_user.reminder_days_before = days
    db_user.reminders_enabled = True
    await session.flush()
    await callback.answer(_("Saved."))
    if callback.message is not None:
        await callback.message.edit_text(
            _("Reminder settings:"), reply_markup=reminder_kb(db_user, _)
        )


@router.callback_query(F.data == "set:dm")
async def cb_dm(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    db_user.dm_enabled = not db_user.dm_enabled
    await session.flush()
    await callback.answer(_("Saved."))
    if callback.message is not None:
        await render_settings(callback.message, session, db_user, _)


@router.callback_query(F.data == "set:group")
async def cb_group(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    db_user.group_enabled = not db_user.group_enabled
    await session.flush()
    await callback.answer(_("Saved."))
    if callback.message is not None:
        await render_settings(callback.message, session, db_user, _)


@router.callback_query(F.data == "set:lang")
async def cb_language(callback: CallbackQuery, db_user: User, _: T) -> None:
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(
            _("Choose the language:"), reply_markup=language_kb(db_user.locale, _)
        )


@router.callback_query(F.data.startswith("set:lang:"))
async def cb_language_set(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    locale = (callback.data or "").split(":")[2]
    if locale not in LOCALE_NAMES:
        await callback.answer(_("Unknown language."), show_alert=True)
        return
    db_user.locale = locale
    await session.flush()
    translator = get_translator(locale)
    await callback.answer(translator.gettext("Saved."))
    if callback.message is not None:
        await render_settings(
            callback.message, session, db_user, translator.gettext, edit=True
        )


@router.callback_query(F.data == "menu:settings")
async def cb_settings_alias(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(_("Choose an action:"), reply_markup=main_menu(_))
        await render_settings(callback.message, session, db_user, _)
