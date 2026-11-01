from __future__ import annotations

from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ChatMemberUpdated, ErrorEvent
from loguru import logger

from dobby.bot.handlers import (
    anniversaries,
    common,
    contacts,
    events,
    groups,
    settings,
    start,
    subscriptions,
)
from dobby.bot.middlewares import (
    DbSessionMiddleware,
    I18nMiddleware,
    MemberTrackerMiddleware,
    ThrottlingMiddleware,
    UserMiddleware,
    track_and_notify,
)
from dobby.config import get_settings
from dobby.i18n import get_translator


async def _on_error(event: ErrorEvent, bot: Bot) -> bool:
    logger.opt(exception=event.exception).error("update handling failed")
    admin_id = get_settings().admin_tg_id
    if admin_id:
        translator = get_translator(get_settings().default_locale)
        text = translator.gettext("⚠️ Bot error: {error}").format(
            error=f"{type(event.exception).__name__}: {event.exception}"
        )
        try:
            await bot.send_message(admin_id, text[:4000])
        except Exception:  # pragma: no cover - best effort
            logger.exception("could not notify admin")
    return True


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.outer_middleware(ThrottlingMiddleware())
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(UserMiddleware())
    dp.update.outer_middleware(I18nMiddleware())
    dp.message.outer_middleware(MemberTrackerMiddleware())

    @dp.chat_member()
    async def on_chat_member(event: ChatMemberUpdated, session: Any, bot: Bot) -> None:
        user = event.new_chat_member.user
        status = getattr(event.new_chat_member.status, "value", event.new_chat_member.status)
        if user.is_bot or status not in ("member", "administrator", "creator"):
            return
        if event.chat.type in ("group", "supergroup"):
            try:
                await track_and_notify(session, bot, event.chat.id, user)
            except Exception:
                logger.exception("member tracking failed")

    dp.include_router(common.router)
    dp.include_router(start.router)
    dp.include_router(events.router)
    dp.include_router(contacts.router)
    dp.include_router(anniversaries.router)
    dp.include_router(subscriptions.router)
    dp.include_router(settings.router)
    dp.include_router(groups.router)

    dp.errors.register(_on_error)
    return dp
