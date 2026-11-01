from __future__ import annotations

from collections.abc import Callable

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.bot.keyboards import main_menu
from dobby.db.models import Chat, User
from dobby.i18n import get_translator
from dobby.services.dates import now_in
from dobby.services.occurrences import events_on, load_sources
from dobby.services.templates import digest_text

router = Router(name="groups")
T = Callable[..., str]


@router.message(Command("bindgroup"))
async def cmd_bind_group(
    message: Message,
    session: AsyncSession,
    db_user: User,
    bot: Bot,
    _: T,
) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(_("Send /bindgroup in the group you want me to post in."))
        return
    if message.from_user is None:
        return

    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    status = getattr(member.status, "value", member.status)
    if status not in ("creator", "administrator"):
        await message.answer(_("Only a group administrator can bind this group."))
        return

    chat = await session.scalar(
        select(Chat).where(
            Chat.owner_id == db_user.id, Chat.tg_chat_id == message.chat.id
        )
    )
    if chat is None:
        count = int(
            await session.scalar(
                select(func.count(Chat.id)).where(Chat.owner_id == db_user.id)
            )
            or 0
        )
        chat = Chat(
            owner_id=db_user.id,
            tg_chat_id=message.chat.id,
            title=message.chat.title,
            type=message.chat.type,
            is_default=count == 0,
        )
        session.add(chat)
    else:
        chat.title = message.chat.title
        chat.type = message.chat.type
    await session.flush()

    await message.answer(
        _("✅ This group is bound. Congratulations will be posted here.")
    )


@router.message(Command("unbindgroup"))
async def cmd_unbind_group(
    message: Message, session: AsyncSession, db_user: User, _: T
) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await message.answer(_("Send /unbindgroup in the group."))
        return
    chat = await session.scalar(
        select(Chat).where(
            Chat.owner_id == db_user.id, Chat.tg_chat_id == message.chat.id
        )
    )
    if chat is None:
        await message.answer(_("This group is not bound."))
        return

    was_default = chat.is_default
    await session.delete(chat)
    await session.flush()

    if was_default:
        replacement = await session.scalar(
            select(Chat).where(Chat.owner_id == db_user.id).order_by(Chat.id).limit(1)
        )
        if replacement is not None:
            replacement.is_default = True
            await session.flush()

    await message.answer(_("🔕 This group will no longer receive congratulations."))


@router.message(F.chat.type.in_({"group", "supergroup"}), F.entities)
async def on_mention(message: Message, session: AsyncSession, bot: Bot) -> None:
    me = await bot.me()
    tag = f"@{me.username}".lower()
    text = message.text or ""
    mentioned = any(
        entity.type == "mention"
        and entity.extract_from(text).lower() == tag
        for entity in message.entities or []
    )
    if not mentioned:
        return

    chats = list(
        await session.scalars(select(Chat).where(Chat.tg_chat_id == message.chat.id))
    )
    logger.info("mention in chat {}: {} bound owner(s)", message.chat.id, len(chats))
    if not chats:
        await message.reply("This group is not bound. An admin should send /bindgroup here.")
        return
    for chat in chats:
        owner = await session.get(User, chat.owner_id)
        if owner is None:
            continue
        tr = get_translator(owner.locale)
        today = now_in(owner.timezone).date()
        sources = await load_sources(session, owner)
        events = [
            event
            for event in events_on(sources, today)
            if event.notify_group and event.target_chat_id == message.chat.id
        ]
        if events:
            await message.reply(digest_text(owner.locale, events))
        else:
            await message.reply(tr.gettext("Nothing to celebrate today."))
        return


@router.message(Command("chats"))
async def cmd_chats(
    message: Message, session: AsyncSession, db_user: User, _: T
) -> None:
    chats = list(
        await session.scalars(select(Chat).where(Chat.owner_id == db_user.id))
    )
    if not chats:
        await message.answer(
            _("No group is bound. Add me to a group and send /bindgroup there."),
            reply_markup=main_menu(_),
        )
        return
    lines = [f"🎉 <b>{_('Bound groups')}</b>", ""]
    for chat in chats:
        mark = "⭐ " if chat.is_default else "• "
        lines.append(f"{mark}{chat.title or chat.tg_chat_id}")
    await message.answer("\n".join(lines), reply_markup=main_menu(_))
