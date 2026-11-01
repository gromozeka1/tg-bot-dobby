from __future__ import annotations

from collections.abc import Callable
from datetime import date
from html import escape
from math import ceil

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.bot.filters import MenuButton
from dobby.bot.keyboards import (
    anniversary_list_kb,
    anniversary_view_kb,
    confirm_kb,
    kind_kb,
    recurring_kb,
    target_kb,
)
from dobby.bot.states import AnniversaryForm, EditAnniversary
from dobby.db.models import Anniversary, Chat, User
from dobby.services import anniversaries as service
from dobby.utils.parsing import ParseError, parse_date, validate_start_date

router = Router(name="anniversaries")
T = Callable[..., str]
PER_PAGE = 5

KINDS = {"wedding": "💍 Wedding", "memorial": "🕯 Memorial", "custom": "🎉 Custom"}


def _pages(total: int) -> int:
    return max(1, ceil(total / PER_PAGE))


def _kind_label(kind: str, _: T) -> str:
    return _(KINDS.get(kind, "🎉 Custom"))


async def _chats(session: AsyncSession, owner_id: int) -> list[Chat]:
    return list(await session.scalars(select(Chat).where(Chat.owner_id == owner_id)))


def anniversary_card(item: Anniversary, _: T) -> str:
    value = f"{item.day:02d}.{item.month:02d}"
    if item.start_year:
        value += f".{item.start_year}"
    lines = [
        f"<b>{escape(item.title)}</b>",
        f"📅 {value}",
        _("🎗 {kind}").format(kind=_kind_label(item.kind, _)),
        _("🔁 Every year") if item.recurring else _("1️⃣ Once"),
        _("📩 Digest: {state}").format(state=_("on") if item.notify_digest else _("off")),
        _("🎉 Group: {state}").format(state=_("on") if item.notify_group else _("off")),
        _("✉️ Direct: {state}").format(state=_("on") if item.notify_direct else _("off")),
    ]
    return "\n".join(lines)


async def _show_item(
    message: Message, item: Anniversary, page: int, _: T, *, prefix: str = ""
) -> None:
    text = anniversary_card(item, _)
    if prefix:
        text = f"{prefix}\n\n{text}"
    await message.answer(text, reply_markup=anniversary_view_kb(item, page, _))


async def render_list(
    message: Message,
    page: int,
    session: AsyncSession,
    user: User,
    _: T,
    *,
    edit: bool = False,
) -> None:
    items, total = await service.list_anniversaries(session, user.id, page)
    pages = _pages(total)
    page = min(max(0, page), pages - 1)
    header = _("🎉 Anniversaries ({total})").format(total=total)
    text = (
        header
        if total
        else f"{header}\n\n{_('No anniversaries yet. Add the first one with /addanniversary.')}"
    )
    keyboard = anniversary_list_kb(items, page, pages, _)
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.message(Command("anniversaries"))
@router.message(MenuButton("🎉 Anniversaries"))
async def cmd_anniversaries(
    message: Message, session: AsyncSession, db_user: User, _: T
) -> None:
    await render_list(message, 0, session, db_user, _)


@router.message(Command("addanniversary"))
async def cmd_add_anniversary(message: Message, state: FSMContext, _: T) -> None:
    await start_anniversary_form(message, state, _)


async def start_anniversary_form(
    event: Message | CallbackQuery, state: FSMContext, _: T
) -> None:
    await state.set_state(AnniversaryForm.title)
    await state.update_data(anniversary_id=None, page=0)
    text = _("What is the occasion? For example: Wedding, Mom's memorial, First date.")
    if isinstance(event, CallbackQuery):
        await event.answer()
        if event.message is not None:
            await event.message.answer(text)
    else:
        await event.answer(text)


@router.message(AnniversaryForm.title)
async def process_title(message: Message, state: FSMContext, _: T) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 255:
        await message.answer(_("Please send a title up to 255 characters."))
        return
    await state.update_data(title=title)
    await state.set_state(AnniversaryForm.date)
    await message.answer(_("Date? For example 12.05 or 12.05.2015."))


@router.message(AnniversaryForm.date)
async def process_date(message: Message, state: FSMContext, _: T) -> None:
    try:
        parsed = parse_date(message.text or "")
        validate_start_date(parsed)
    except ParseError:
        await message.answer(_("Invalid date. Try 12.05 or 12.05.2015."))
        return
    await state.update_data(
        day=parsed.day, month=parsed.month, start_year=parsed.year
    )
    await state.set_state(AnniversaryForm.kind)
    await message.answer(_("What kind of date is this?"), reply_markup=kind_kb(_))


@router.callback_query(AnniversaryForm.kind, F.data.startswith("kind:"))
async def process_kind(
    callback: CallbackQuery, state: FSMContext, _: T
) -> None:
    kind = (callback.data or "").split(":", 1)[1]
    await state.update_data(kind=kind)
    data = await state.get_data()
    await callback.answer()
    if callback.message is None:
        return
    if data.get("start_year") is None:
        await state.set_state(AnniversaryForm.start_year)
        await callback.message.edit_text(
            _("Start year? Send «-» if you don't know.")
        )
    else:
        await state.set_state(AnniversaryForm.recurring)
        await callback.message.edit_text(
            _("Repeat every year?"), reply_markup=recurring_kb(_)
        )


@router.message(AnniversaryForm.start_year)
async def process_start_year(message: Message, state: FSMContext, _: T) -> None:
    value = (message.text or "").strip()
    if value in {"-", "—", "нет", "no", "skip", "0"}:
        year = None
    else:
        try:
            year = int(value)
        except ValueError:
            await message.answer(_("Invalid year. Send a year like 2015 or «-»."))
            return
        if year < 1900 or year > date.today().year:
            await message.answer(_("Invalid year. Send a year like 2015 or «-»."))
            return
    await state.update_data(start_year=year)
    await state.set_state(AnniversaryForm.recurring)
    await message.answer(_("Repeat every year?"), reply_markup=recurring_kb(_))


@router.callback_query(AnniversaryForm.recurring, F.data.startswith("rec:"))
async def process_recurring(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    recurring = (callback.data or "").split(":", 1)[1] == "1"
    await state.update_data(recurring=recurring)
    chats = await _chats(session, db_user.id)
    await state.set_state(AnniversaryForm.target)
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(
            _("Where should I congratulate?"), reply_markup=target_kb(chats, _)
        )


@router.callback_query(AnniversaryForm.target, F.data.startswith("tgt:"))
async def process_target(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    value = (callback.data or "").split(":", 1)[1]
    if value == "none":
        await state.update_data(
            target_chat_id=None, target_title=None, notify_group=False
        )
    else:
        chat = await session.get(Chat, int(value))
        if chat is None or chat.owner_id != db_user.id:
            await callback.answer(_("This group is no longer available."), show_alert=True)
            return
        await state.update_data(
            target_chat_id=chat.id, target_title=chat.title, notify_group=True
        )

    data = await state.get_data()
    await state.set_state(AnniversaryForm.confirm)
    value = f"{data['day']:02d}.{data['month']:02d}"
    if data.get("start_year"):
        value += f".{data['start_year']}"
    target = data.get("target_title") or _("Digest only")
    text = (
        f"<b>{_('Check the data:')}</b>\n\n"
        + _("Title: {title}").format(title=escape(data["title"]))
        + "\n"
        + _("Date: {date}").format(date=value)
        + "\n"
        + _("Kind: {kind}").format(kind=_kind_label(data.get("kind", "custom"), _))
        + "\n"
        + _("Repeat: {value}").format(
            value=_("every year") if data.get("recurring", True) else _("once")
        )
        + "\n"
        + _("Group: {chat}").format(chat=escape(str(target)))
    )
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=confirm_kb("ca", _))


@router.callback_query(AnniversaryForm.confirm, F.data == "ca:no")
async def cancel_anniversary(callback: CallbackQuery, state: FSMContext, _: T) -> None:
    await state.clear()
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(_("Cancelled. Nothing was saved."))


@router.callback_query(AnniversaryForm.confirm, F.data == "ca:yes")
async def save_anniversary(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    data = await state.get_data()
    start_year = data.get("start_year")
    recurring = bool(data.get("recurring", True))
    if not recurring and start_year is None:
        start_year = date.today().year
    item = await service.create_anniversary(
        session,
        db_user.id,
        title=data["title"],
        day=data["day"],
        month=data["month"],
        start_year=start_year,
        kind=data.get("kind", "custom"),
        recurring=recurring,
        target_chat_id=data.get("target_chat_id"),
        notify_group=bool(data.get("notify_group", True)),
    )
    await state.clear()
    await callback.answer(_("Saved."))
    if callback.message is not None:
        await callback.message.edit_text(_("✅ Saved."))
        await _show_item(callback.message, item, 0, _, prefix=_("New anniversary"))


@router.callback_query(F.data.startswith("a:page:"))
async def cb_page(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    page = int((callback.data or "").split(":")[2])
    await callback.answer()
    if callback.message is not None:
        await render_list(callback.message, page, session, db_user, _, edit=True)


@router.callback_query(F.data.startswith("a:view:"))
async def cb_view(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    item_id = int((callback.data or "").split(":")[2])
    item = await service.get_anniversary(session, db_user.id, item_id)
    await callback.answer()
    if item is None or callback.message is None:
        return
    await callback.message.edit_text(
        anniversary_card(item, _), reply_markup=anniversary_view_kb(item, 0, _)
    )


@router.callback_query(F.data.startswith("a:mute:"))
async def cb_mute(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    item_id = int((callback.data or "").split(":")[2])
    item = await service.get_anniversary(session, db_user.id, item_id)
    await callback.answer()
    if item is None or callback.message is None:
        return
    any_enabled = item.notify_digest or item.notify_group or item.notify_direct
    await service.set_anniversary_channels(
        session,
        item,
        digest=not any_enabled,
        group=not any_enabled,
        direct=False,
    )
    await callback.message.edit_text(
        anniversary_card(item, _), reply_markup=anniversary_view_kb(item, 0, _)
    )


@router.callback_query(F.data.startswith("a:del:"))
async def cb_delete(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    item_id = int((callback.data or "").split(":")[2])
    item = await service.get_anniversary(session, db_user.id, item_id)
    await callback.answer()
    if item is None or callback.message is None:
        return
    await callback.message.edit_text(
        _("Delete {name}?").format(name=escape(item.title)),
        reply_markup=confirm_kb(f"dela:{item.id}", _),
    )


@router.callback_query(F.data.startswith("dela:"))
async def cb_delete_confirm(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    parts = (callback.data or "").split(":")
    action, item_id = parts[2], int(parts[1])
    item = await service.get_anniversary(session, db_user.id, item_id)
    await callback.answer()
    if item is None or callback.message is None:
        return
    if action == "yes":
        await service.delete_anniversary(session, item)
        await callback.message.edit_text(_("🗑 Deleted."))
        await render_list(callback.message, 0, session, db_user, _, edit=False)
    else:
        await callback.message.edit_text(
            anniversary_card(item, _), reply_markup=anniversary_view_kb(item, 0, _)
        )


@router.callback_query(F.data.startswith("a:edittitle:"))
async def cb_edit_title(callback: CallbackQuery, state: FSMContext, _: T) -> None:
    item_id = int((callback.data or "").split(":")[2])
    await state.set_state(EditAnniversary.title)
    await state.update_data(anniversary_id=item_id)
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(_("Send a new title."))


@router.message(EditAnniversary.title)
async def save_edit_title(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 255:
        await message.answer(_("Please send a title up to 255 characters."))
        return
    data = await state.get_data()
    item = await service.get_anniversary(session, db_user.id, int(data["anniversary_id"]))
    if item is None:
        await state.clear()
        await message.answer(_("Anniversary not found."))
        return
    item.title = title
    await session.flush()
    await state.clear()
    await _show_item(message, item, 0, _, prefix=_("✅ Saved."))


@router.callback_query(F.data.startswith("a:editdate:"))
async def cb_edit_date(callback: CallbackQuery, state: FSMContext, _: T) -> None:
    item_id = int((callback.data or "").split(":")[2])
    await state.set_state(EditAnniversary.date)
    await state.update_data(anniversary_id=item_id)
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(_("Send a new date: 12.05 or 12.05.2015."))


@router.message(EditAnniversary.date)
async def save_edit_date(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User, _: T
) -> None:
    try:
        parsed = parse_date(message.text or "")
        validate_start_date(parsed)
    except ParseError:
        await message.answer(_("Invalid date. Try 12.05 or 12.05.2015."))
        return
    data = await state.get_data()
    item = await service.get_anniversary(session, db_user.id, int(data["anniversary_id"]))
    if item is None:
        await state.clear()
        await message.answer(_("Anniversary not found."))
        return
    item.day = parsed.day
    item.month = parsed.month
    if parsed.year is not None:
        item.start_year = parsed.year
    await session.flush()
    await state.clear()
    await _show_item(message, item, 0, _, prefix=_("✅ Saved."))
