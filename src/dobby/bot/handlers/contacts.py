from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from html import escape
from math import ceil

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.bot.filters import MenuButton
from dobby.bot.keyboards import (
    confirm_kb,
    contact_list_kb,
    contact_view_kb,
    relation_kb,
    target_kb,
)
from dobby.bot.states import ContactForm, EditContact
from dobby.db.models import Chat, Contact, GroupMember, User
from dobby.services import contacts as service
from dobby.utils.parsing import ParsedDate, ParseError, parse_date, validate_birth_date

router = Router(name="contacts")
T = Callable[..., str]
PER_PAGE = 5

RELATIONS = {
    "family": "Family",
    "friend": "Friend",
    "colleague": "Colleague",
    "other": "Other",
}


def _pages(total: int) -> int:
    return max(1, ceil(total / PER_PAGE))


def _relation_label(code: str | None, _: T) -> str:
    if not code:
        return "—"
    return _(RELATIONS.get(code, "Other"))


async def _chats(session: AsyncSession, owner_id: int) -> list[Chat]:
    return list(await session.scalars(select(Chat).where(Chat.owner_id == owner_id)))


def contact_card(contact: Contact, _: T) -> str:
    date = f"{contact.day:02d}.{contact.month:02d}"
    if contact.birth_year:
        date += f".{contact.birth_year}"
    lines = [f"<b>{escape(contact.full_name)}</b>", f"🎂 {date}"]
    if contact.relationship:
        lines.append(_("👥 {relation}").format(relation=_relation_label(contact.relationship, _)))
    if contact.telegram_user_id:
        lines.append(_("Telegram ID: {id}").format(id=contact.telegram_user_id))
    lines.append(
        _("📩 Digest: {state}").format(state=_("on") if contact.notify_digest else _("off"))
    )
    lines.append(_("🎉 Group: {state}").format(state=_("on") if contact.notify_group else _("off")))
    lines.append(
        _("✉️ Direct: {state}").format(state=_("on") if contact.notify_direct else _("off"))
    )
    return "\n".join(lines)


async def _show_contact(
    message: Message, contact: Contact, page: int, _: T, *, prefix: str = ""
) -> None:
    text = contact_card(contact, _)
    if prefix:
        text = f"{prefix}\n\n{text}"
    await message.answer(text, reply_markup=contact_view_kb(contact, page, _))


async def render_list(
    message: Message,
    page: int,
    session: AsyncSession,
    user: User,
    _: T,
    *,
    edit: bool = False,
) -> None:
    items, total = await service.list_contacts(session, user.id, page)
    pages = _pages(total)
    page = min(max(0, page), pages - 1)
    header = _("👥 Contacts ({total})").format(total=total)
    text = (
        header
        if total
        else f"{header}\n\n{_('No contacts yet. Add the first one with /addcontact.')}"
    )
    keyboard = contact_list_kb(items, page, pages, _)
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.message(Command("contacts"))
@router.message(MenuButton("👥 Contacts"))
async def cmd_contacts(message: Message, session: AsyncSession, db_user: User, _: T) -> None:
    await render_list(message, 0, session, db_user, _)


@router.message(Command("addcontact"))
async def cmd_add_contact(message: Message, state: FSMContext, _: T) -> None:
    await start_contact_form(message, state, _)


async def start_contact_form(event: Message | CallbackQuery, state: FSMContext, _: T) -> None:
    await state.set_state(ContactForm.name)
    await state.update_data(contact_id=None, page=0)
    text = _("What is the name? Send /cancel to abort.")
    if isinstance(event, CallbackQuery):
        await event.answer()
        if event.message is not None:
            await event.message.answer(text)
    else:
        await event.answer(text)


@router.message(ContactForm.name)
async def process_name(message: Message, state: FSMContext, _: T) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 255:
        await message.answer(_("Please send a name up to 255 characters."))
        return
    await state.update_data(full_name=name)
    await state.set_state(ContactForm.tg_id)
    await message.answer(
        _(
            "Telegram ID or @username of this person? It is used to mention them in the "
            "group and to look up their birthday. Send «-» to skip."
        )
    )


async def _ask_date(message: Message, state: FSMContext, _: T) -> None:
    await state.set_state(ContactForm.date)
    await message.answer(
        _("Date of birth? For example 12.05 or 12.05.1990. Send /cancel to abort.")
    )


@router.message(ContactForm.tg_id)
async def process_tg_id(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession, db_user: User, _: T
) -> None:
    value = (message.text or "").strip()
    if value in {"-", "—", "нет", "no", "skip"}:
        await state.update_data(telegram_user_id=None)
        await _ask_date(message, state, _)
        return
    username = value.removeprefix("https://t.me/").removeprefix("@")
    if value.isdigit():
        if not 0 < int(value) < 2**52:
            await message.answer(_("Invalid ID. Send a number like 123456789 or «-»."))
            return
        lookup: int | str = int(value)
    elif re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", username):
        lookup = f"@{username}"
    else:
        await message.answer(_("Invalid ID. Send a number like 123456789 or «-»."))
        return

    birthdate = None
    tg_id = lookup if isinstance(lookup, int) else None
    if tg_id is None:
        tg_id = await session.scalar(
            select(GroupMember.tg_user_id)
            .join(Chat, Chat.id == GroupMember.chat_id)
            .where(
                Chat.owner_id == db_user.id, func.lower(GroupMember.username) == username.lower()
            )
            .limit(1)
        )
        if tg_id is not None:
            lookup = tg_id
    try:
        chat = await bot.get_chat(lookup)
        tg_id = chat.id
        birthdate = chat.birthdate
        logger.info("get_chat({}): type={} birthdate={}", lookup, chat.type, birthdate)
    except TelegramAPIError as exc:
        logger.info("get_chat({}) failed: {}", lookup, exc)
    if tg_id is None:
        await message.answer(
            _("Could not find this username. Send the numeric Telegram ID instead, or «-».")
        )
        return
    await state.update_data(telegram_user_id=tg_id)
    if birthdate is not None:
        try:
            validate_birth_date(ParsedDate(birthdate.day, birthdate.month, birthdate.year))
        except ParseError:
            birthdate = None
    if birthdate is None:
        await message.answer(_("Could not get the birthday from Telegram, please enter it."))
        await _ask_date(message, state, _)
        return

    await state.update_data(day=birthdate.day, month=birthdate.month, birth_year=birthdate.year)
    await message.answer(
        _("Birthday from Telegram profile: {date}").format(
            date=f"{birthdate.day:02d}.{birthdate.month:02d}"
            + (f".{birthdate.year}" if birthdate.year else "")
        )
    )
    await _ask_relation(message, state, _)


async def _ask_relation(message: Message, state: FSMContext, _: T) -> None:
    await state.set_state(ContactForm.relation)
    await message.answer(_("Relation?"), reply_markup=relation_kb(_))


@router.message(ContactForm.date)
async def process_date(message: Message, state: FSMContext, _: T) -> None:
    try:
        parsed = parse_date(message.text or "")
        validate_birth_date(parsed)
    except ParseError:
        await message.answer(_("Invalid date. Try 12.05 or 12.05.1990."))
        return

    await state.update_data(day=parsed.day, month=parsed.month, birth_year=parsed.year)
    if parsed.year is None:
        await state.set_state(ContactForm.year)
        await message.answer(_("Birth year? Send «-» if you don't know."))
    else:
        await _ask_relation(message, state, _)


@router.message(ContactForm.year)
async def process_year(message: Message, state: FSMContext, _: T) -> None:
    value = (message.text or "").strip()
    if value in {"-", "—", "нет", "no", "skip", "0"}:
        year = None
    else:
        try:
            year = int(value)
        except ValueError:
            await message.answer(_("Invalid year. Send a year like 1990 or «-»."))
            return
        if year < 1900 or year > date.today().year:
            await message.answer(_("Invalid year. Send a year like 1990 or «-»."))
            return

    await state.update_data(birth_year=year)
    await _ask_relation(message, state, _)


@router.callback_query(ContactForm.relation, F.data.startswith("rel:"))
async def process_relation(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    value = (callback.data or "").split(":", 1)[1]
    relationship = None if value == "skip" else value
    await state.update_data(relationship=relationship)
    chats = await _chats(session, db_user.id)
    await state.set_state(ContactForm.target)
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(
            _("Where should I congratulate?"), reply_markup=target_kb(chats, _)
        )


@router.callback_query(ContactForm.target, F.data.startswith("tgt:"))
async def process_target(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    value = (callback.data or "").split(":", 1)[1]
    if value == "none":
        await state.update_data(target_chat_id=None, target_title=None, notify_group=False)
    else:
        chat = await session.get(Chat, int(value))
        if chat is None or chat.owner_id != db_user.id:
            await callback.answer(_("This group is no longer available."), show_alert=True)
            return
        await state.update_data(target_chat_id=chat.id, target_title=chat.title, notify_group=True)

    data = await state.get_data()
    await state.set_state(ContactForm.confirm)
    name = escape(data["full_name"])
    date = f"{data['day']:02d}.{data['month']:02d}"
    if data.get("birth_year"):
        date += f".{data['birth_year']}"
    relation = _relation_label(data.get("relationship"), _)
    target = data.get("target_title") or _("Digest only")
    text = (
        f"<b>{_('Check the data:')}</b>\n\n"
        + _("Name: {name}").format(name=name)
        + "\n"
        + _("Date: {date}").format(date=date)
        + "\n"
        + _("Relation: {relation}").format(relation=relation)
        + "\n"
        + _("Group: {chat}").format(chat=escape(str(target)))
    )
    if data.get("telegram_user_id"):
        text += "\n" + _("Telegram ID: {id}").format(id=data["telegram_user_id"])
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=confirm_kb("cc", _))


@router.callback_query(ContactForm.confirm, F.data == "cc:no")
async def cancel_contact(callback: CallbackQuery, state: FSMContext, _: T) -> None:
    await state.clear()
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(_("Cancelled. Nothing was saved."))


@router.callback_query(ContactForm.confirm, F.data == "cc:yes")
async def save_contact(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    data = await state.get_data()
    contact = await service.create_contact(
        session,
        db_user.id,
        full_name=data["full_name"],
        day=data["day"],
        month=data["month"],
        birth_year=data.get("birth_year"),
        relationship=data.get("relationship"),
        target_chat_id=data.get("target_chat_id"),
        notify_group=bool(data.get("notify_group", True)),
        telegram_user_id=data.get("telegram_user_id"),
    )
    await state.clear()
    await callback.answer(_("Saved."))
    if callback.message is not None:
        await callback.message.edit_text(_("✅ Saved."))
        await _show_contact(callback.message, contact, 0, _, prefix=_("New contact"))


@router.callback_query(F.data.startswith("c:page:"))
async def cb_page(callback: CallbackQuery, session: AsyncSession, db_user: User, _: T) -> None:
    page = int((callback.data or "").split(":")[2])
    await callback.answer()
    if callback.message is not None:
        await render_list(callback.message, page, session, db_user, _, edit=True)


@router.callback_query(F.data.startswith("c:view:"))
async def cb_view(callback: CallbackQuery, session: AsyncSession, db_user: User, _: T) -> None:
    contact_id = int((callback.data or "").split(":")[2])
    contact = await service.get_contact(session, db_user.id, contact_id)
    await callback.answer()
    if contact is None or callback.message is None:
        return
    await callback.message.edit_text(
        contact_card(contact, _), reply_markup=contact_view_kb(contact, 0, _)
    )


@router.callback_query(F.data.startswith("c:mute:"))
async def cb_mute(callback: CallbackQuery, session: AsyncSession, db_user: User, _: T) -> None:
    contact_id = int((callback.data or "").split(":")[2])
    contact = await service.get_contact(session, db_user.id, contact_id)
    await callback.answer()
    if contact is None or callback.message is None:
        return
    any_enabled = contact.notify_digest or contact.notify_group or contact.notify_direct
    await service.set_contact_channels(
        session,
        contact,
        digest=not any_enabled,
        group=not any_enabled,
        direct=False,
    )
    await callback.message.edit_text(
        contact_card(contact, _), reply_markup=contact_view_kb(contact, 0, _)
    )


@router.callback_query(F.data.startswith("c:del:"))
async def cb_delete(callback: CallbackQuery, session: AsyncSession, db_user: User, _: T) -> None:
    contact_id = int((callback.data or "").split(":")[2])
    contact = await service.get_contact(session, db_user.id, contact_id)
    await callback.answer()
    if contact is None or callback.message is None:
        return
    await callback.message.edit_text(
        _("Delete {name}?").format(name=escape(contact.full_name)),
        reply_markup=confirm_kb(f"delc:{contact.id}", _),
    )


@router.callback_query(F.data.startswith("delc:"))
async def cb_delete_confirm(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    parts = (callback.data or "").split(":")
    action, contact_id = parts[2], int(parts[1])
    contact = await service.get_contact(session, db_user.id, contact_id)
    await callback.answer()
    if contact is None or callback.message is None:
        return
    if action == "yes":
        await service.delete_contact(session, contact)
        await callback.message.edit_text(_("🗑 Deleted."))
        await render_list(callback.message, 0, session, db_user, _, edit=False)
    else:
        await callback.message.edit_text(
            contact_card(contact, _), reply_markup=contact_view_kb(contact, 0, _)
        )


@router.callback_query(F.data.startswith("c:editname:"))
async def cb_edit_name(callback: CallbackQuery, state: FSMContext, _: T) -> None:
    contact_id = int((callback.data or "").split(":")[2])
    await state.set_state(EditContact.name)
    await state.update_data(contact_id=contact_id)
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(_("Send a new name."))


@router.message(EditContact.name)
async def save_edit_name(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 255:
        await message.answer(_("Please send a name up to 255 characters."))
        return
    data = await state.get_data()
    contact = await service.get_contact(session, db_user.id, int(data["contact_id"]))
    if contact is None:
        await state.clear()
        await message.answer(_("Contact not found."))
        return
    contact.full_name = name
    await session.flush()
    await state.clear()
    await _show_contact(message, contact, 0, _, prefix=_("✅ Saved."))


@router.callback_query(F.data.startswith("c:editdate:"))
async def cb_edit_date(callback: CallbackQuery, state: FSMContext, _: T) -> None:
    contact_id = int((callback.data or "").split(":")[2])
    await state.set_state(EditContact.date)
    await state.update_data(contact_id=contact_id)
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(_("Send a new date: 12.05 or 12.05.1990."))


@router.message(EditContact.date)
async def save_edit_date(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    try:
        parsed = parse_date(message.text or "")
        validate_birth_date(parsed)
    except ParseError:
        await message.answer(_("Invalid date. Try 12.05 or 12.05.1990."))
        return
    data = await state.get_data()
    contact = await service.get_contact(session, db_user.id, int(data["contact_id"]))
    if contact is None:
        await state.clear()
        await message.answer(_("Contact not found."))
        return
    contact.day = parsed.day
    contact.month = parsed.month
    if parsed.year is not None:
        contact.birth_year = parsed.year
    await session.flush()
    await state.clear()
    await _show_contact(message, contact, 0, _, prefix=_("✅ Saved."))


@router.callback_query(F.data.startswith("c:edittg:"))
async def cb_edit_tg(callback: CallbackQuery, state: FSMContext, _: T) -> None:
    contact_id = int((callback.data or "").split(":")[2])
    await state.set_state(EditContact.tg_id)
    await state.update_data(contact_id=contact_id)
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(_("Send the Telegram ID, or «-» to remove it."))


@router.message(EditContact.tg_id)
async def save_edit_tg(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    value = (message.text or "").strip()
    tg_id = None
    if value not in {"-", "—", "нет", "no", "skip"}:
        if not value.isdigit() or not 0 < int(value) < 2**52:
            await message.answer(_("Invalid ID. Send a number like 123456789 or «-»."))
            return
        tg_id = int(value)
    data = await state.get_data()
    contact = await service.get_contact(session, db_user.id, int(data["contact_id"]))
    if contact is None:
        await state.clear()
        await message.answer(_("Contact not found."))
        return
    contact.telegram_user_id = tg_id
    await session.flush()
    await state.clear()
    await _show_contact(message, contact, 0, _, prefix=_("✅ Saved."))
