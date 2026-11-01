from __future__ import annotations

from collections.abc import Callable

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.bot.filters import MenuButton
from dobby.db.models import User
from dobby.services.dates import now_in
from dobby.services.occurrences import events_on, load_sources, upcoming
from dobby.services.templates import digest_text, upcoming_text

router = Router(name="events")
T = Callable[..., str]


@router.message(Command("today"))
@router.message(MenuButton("📅 Today"))
async def cmd_today(
    message: Message, session: AsyncSession, db_user: User, _: T
) -> None:
    today = now_in(db_user.timezone).date()
    sources = await load_sources(session, db_user)
    events = events_on(sources, today)
    if not events:
        await message.answer(_("Nothing to celebrate today."))
        return
    await message.answer(digest_text(db_user.locale, events))


@router.message(Command("upcoming"))
async def cmd_upcoming(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    db_user: User,
    _: T,
) -> None:
    window = 14
    if command.args:
        try:
            window = int(command.args.strip())
        except ValueError:
            await message.answer(_("Send a number of days, for example /upcoming 30."))
            return
    window = max(1, min(window, 60))

    today = now_in(db_user.timezone).date()
    sources = await load_sources(session, db_user)
    days = upcoming(sources, today, window)
    if not days:
        await message.answer(
            _("No events in the next {n} days.").format(n=window)
        )
        return
    await message.answer(upcoming_text(db_user.locale, days, window))
