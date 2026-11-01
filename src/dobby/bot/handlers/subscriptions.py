from __future__ import annotations

from collections.abc import Callable
from html import escape
from math import ceil

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.bot.filters import MenuButton
from dobby.bot.keyboards import (
    subscription_detail_kb,
    subscriptions_list_kb,
)
from dobby.db.models import Chat, User
from dobby.services.subscriptions import (
    SubItem,
    bulk_mute,
    list_items,
    toggle_channel,
)

router = Router(name="subscriptions")
T = Callable[..., str]
PER_PAGE = 6


def _pages(total: int) -> int:
    return max(1, ceil(total / PER_PAGE))


def _icon(item: SubItem) -> str:
    return "🎂" if item.kind == "birthday" else "💍"


async def _all_items(session: AsyncSession, owner_id: int) -> list[SubItem]:
    return await list_items(session, owner_id, "all")


def _find(items: list[SubItem], kind: str, item_id: int) -> SubItem | None:
    return next(
        (item for item in items if item.kind == kind and item.id == item_id), None
    )


def _detail_text(item: SubItem, _: T) -> str:
    kind = _("🎂 Birthday") if item.kind == "birthday" else _("💍 Anniversary")
    date = f"{item.day:02d}.{item.month:02d}"
    lines = [
        f"<b>{escape(item.title)}</b>",
        f"{kind} · {date}",
        "",
        _("📩 Digest: {state}").format(state=_("on") if item.notify_digest else _("off")),
        _("🎉 Group: {state}").format(state=_("on") if item.notify_group else _("off")),
        _("✉️ Direct: {state}").format(state=_("on") if item.notify_direct else _("off")),
    ]
    if item.notify_direct:
        lines += ["", _("Direct messages work only after the person starts the bot.")]
    return "\n".join(lines)


async def render_list(
    message: Message,
    session: AsyncSession,
    user: User,
    filter_name: str,
    page: int,
    _: T,
    *,
    edit: bool = False,
) -> None:
    items = await list_items(session, user.id, filter_name)
    pages = _pages(len(items))
    page = min(max(0, page), pages - 1)
    visible = items[page * PER_PAGE : (page + 1) * PER_PAGE]

    lines = [
        f"🔔 <b>{_('Subscriptions')}</b>",
        "",
        _("Choose an event to manage its channels."),
        _("📩 digest · 🎉 group · ✉️ direct"),
    ]
    if not visible:
        lines += ["", _("No events here.")]

    chat_count = int(
        await session.scalar(
            select(func.count(Chat.id)).where(Chat.owner_id == user.id)
        )
        or 0
    )
    keyboard = subscriptions_list_kb(
        visible, page, pages, filter_name, chat_count, _
    )
    text = "\n".join(lines)
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


async def render_detail(
    message: Message,
    session: AsyncSession,
    user: User,
    kind: str,
    item_id: int,
    filter_name: str,
    page: int,
    _: T,
) -> None:
    item = _find(await _all_items(session, user.id), kind, item_id)
    if item is None:
        await message.edit_text(_("Event not found."))
        return
    await message.edit_text(
        _detail_text(item, _),
        reply_markup=subscription_detail_kb(item, filter_name, page, _),
    )


@router.message(Command("subscriptions"))
@router.message(MenuButton("🔔 Subscriptions"))
async def cmd_subscriptions(
    message: Message, session: AsyncSession, db_user: User, _: T
) -> None:
    await render_list(message, session, db_user, "all", 0, _)


@router.callback_query(F.data.startswith("sub:list:"))
async def cb_list(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    _, _, filter_name, page = (callback.data or "").split(":")
    await callback.answer()
    if callback.message is not None:
        await render_list(
            callback.message, session, db_user, filter_name, int(page), _, edit=True
        )


@router.callback_query(F.data.startswith("sub:item:"))
async def cb_item(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    _, _, kind, item_id, filter_name, page = (callback.data or "").split(":")
    await callback.answer()
    if callback.message is not None:
        await render_detail(
            callback.message,
            session,
            db_user,
            kind,
            int(item_id),
            filter_name,
            int(page),
            _,
        )


@router.callback_query(F.data.startswith("sub:t:"))
async def cb_toggle(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    _, _, kind, item_id, channel, filter_name, page = (callback.data or "").split(":")
    value = await toggle_channel(session, db_user.id, kind, int(item_id), channel)
    if value is None:
        await callback.answer(_("Event not found."), show_alert=True)
        return
    await callback.answer(_("Updated."))
    if callback.message is not None:
        await render_detail(
            callback.message,
            session,
            db_user,
            kind,
            int(item_id),
            filter_name,
            int(page),
            _,
        )


@router.callback_query(F.data.startswith("sub:bulk:"))
async def cb_bulk(
    callback: CallbackQuery, session: AsyncSession, db_user: User, _: T
) -> None:
    _, _, kind, mute_value, filter_name = (callback.data or "").split(":")
    await bulk_mute(session, db_user.id, kind, mute=bool(int(mute_value)))
    await callback.answer(_("Updated."))
    if callback.message is not None:
        await render_list(
            callback.message, session, db_user, filter_name, 0, _, edit=True
        )
