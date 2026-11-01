from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from html import escape
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import TelegramObject
from loguru import logger

from dobby.config import get_settings
from dobby.db.session import get_session_factory
from dobby.i18n import get_translator, normalize_locale
from dobby.services.contacts import get_or_create_user
from dobby.services.members import track_member


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 0.4) -> None:
        self.rate = rate
        self._last: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is not None:
            now = time.monotonic()
            previous = self._last.get(tg_user.id, 0.0)
            if now - previous < self.rate:
                return None
            self._last[tg_user.id] = now
        return await handler(event, data)


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with get_session_factory()() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        session = data.get("session")
        if tg_user is None or session is None:
            return await handler(event, data)
        data["db_user"] = await get_or_create_user(session, tg_user)
        return await handler(event, data)


class MemberTrackerMiddleware(BaseMiddleware):
    """Passively records senders of group messages and imports them as contacts."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            await self._track(event, data)
        except Exception:
            logger.exception("member tracking failed")
        return await handler(event, data)

    async def _track(self, event: TelegramObject, data: dict[str, Any]) -> None:
        user = getattr(event, "from_user", None)
        chat = getattr(event, "chat", None)
        session = data.get("session")
        bot = data.get("bot")
        if user is None or chat is None or session is None or bot is None or user.is_bot:
            return
        if chat.type not in ("group", "supergroup"):
            return
        await track_and_notify(session, bot, chat.id, user)


async def track_and_notify(session: Any, bot: Any, tg_chat_id: int, user: Any) -> None:
    async def fetch() -> tuple[int, int, int | None] | None:
        try:
            profile = await bot.get_chat(user.id)
        except TelegramAPIError as exc:
            logger.info("get_chat({}) failed: {}", user.id, exc)
            return None
        birthdate = profile.birthdate
        if birthdate is None:
            return None
        return birthdate.day, birthdate.month, birthdate.year

    imported = await track_member(
        session,
        tg_chat_id=tg_chat_id,
        tg_user_id=user.id,
        full_name=user.full_name,
        username=user.username,
        fetch_birthday=fetch,
    )
    for item in imported:
        logger.info("imported {} from chat {}", item.contact.full_name, tg_chat_id)
        tr = get_translator(item.owner.locale)
        text = tr.gettext("➕ Added {name} from {group} to contacts: {date}").format(
            name=escape(item.contact.full_name),
            group=escape(item.chat.title or str(item.chat.tg_chat_id)),
            date=f"{item.contact.day:02d}.{item.contact.month:02d}"
            + (f".{item.contact.birth_year}" if item.contact.birth_year else ""),
        )
        try:
            await bot.send_message(item.owner.tg_id, text)
        except TelegramAPIError:
            logger.info("could not notify owner about imported contact")


class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        settings = get_settings()
        user = data.get("db_user")
        locale = normalize_locale(
            user.locale if user is not None else settings.default_locale
        )
        translator = get_translator(locale)
        data["locale"] = locale
        data["_"] = translator.gettext
        data["ngettext"] = translator.ngettext
        return await handler(event, data)
