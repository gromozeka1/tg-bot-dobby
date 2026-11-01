from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.db.models import NotificationLog, User
from dobby.db.session import session_scope
from dobby.services.dates import now_in, parse_hhmm
from dobby.services.occurrences import events_on, load_sources
from dobby.services.templates import digest_text, group_text, reminder_text

MAX_ATTEMPTS = 3
RETRY_DELAY = timedelta(minutes=10)
DAY_END = time(23, 59)
MAX_MESSAGE_LEN = 4000


def _cut(text: str) -> str:
    return text if len(text) <= MAX_MESSAGE_LEN else text[: MAX_MESSAGE_LEN - 1] + "…"


async def _get_or_create_log(
    session: AsyncSession,
    *,
    owner_id: int,
    event_type: str,
    event_id: int,
    occurrence_date: date,
    target_chat_id: int,
) -> NotificationLog:
    log = await session.scalar(
        select(NotificationLog).where(
            NotificationLog.owner_id == owner_id,
            NotificationLog.event_type == event_type,
            NotificationLog.event_id == event_id,
            NotificationLog.occurrence_date == occurrence_date,
            NotificationLog.target_chat_id == target_chat_id,
        )
    )
    if log is not None:
        return log
    log = NotificationLog(
        owner_id=owner_id,
        event_type=event_type,
        event_id=event_id,
        occurrence_date=occurrence_date,
        target_chat_id=target_chat_id,
    )
    session.add(log)
    await session.flush()
    return log


def _can_attempt(log: NotificationLog, now_utc: datetime) -> bool:
    if log.status == "sent":
        return False
    if log.attempts >= MAX_ATTEMPTS:
        return False
    if log.attempts == 0 or log.last_attempt_at is None:
        return True
    last_attempt = log.last_attempt_at
    if last_attempt.tzinfo is None:
        last_attempt = last_attempt.replace(tzinfo=UTC)
    return now_utc >= last_attempt + RETRY_DELAY


async def _deliver(
    bot: Bot,
    session: AsyncSession,
    log: NotificationLog,
    *,
    chat_id: int,
    text: str,
    now_utc: datetime,
) -> bool:
    if not _can_attempt(log, now_utc):
        return False
    log.attempts += 1
    log.last_attempt_at = now_utc
    log.status = "pending"
    log.error = None
    await session.commit()
    try:
        message = await bot.send_message(chat_id, _cut(text))
    except TelegramAPIError as exc:
        log.status = "failed"
        log.error = f"{type(exc).__name__}: {exc}"[:500]
        logger.warning(
            "send failed owner={} type={} event={} attempt={}: {}",
            log.owner_id,
            log.event_type,
            log.event_id,
            log.attempts,
            exc,
        )
        return False
    except Exception as exc:  # network / unexpected: retry later
        log.status = "failed"
        log.error = f"{type(exc).__name__}: {exc}"[:500]
        logger.exception("unexpected send error owner={}", log.owner_id)
        return False

    log.status = "sent"
    log.telegram_message_id = message.message_id
    log.sent_at = now_utc
    log.error = None
    return True


async def _skip(session: AsyncSession, log: NotificationLog) -> None:
    log.status = "skipped"
    log.sent_at = datetime.now(UTC)
    await session.flush()


async def run_user(
    bot: Bot, session: AsyncSession, user: User, now_utc: datetime | None = None
) -> None:
    now_utc = now_utc or datetime.now(UTC)
    local = now_in(user.timezone, now=now_utc)
    today = local.date()

    try:
        start_at = parse_hhmm(user.digest_time)
    except ValueError:
        start_at = time(9, 0)
    if local.time() < start_at or local.time() >= DAY_END:
        return

    sources = await load_sources(session, user)
    events = events_on(sources, today)

    if user.dm_enabled:
        digest_events = [event for event in events if event.notify_digest]
        log = await _get_or_create_log(
            session,
            owner_id=user.id,
            event_type="digest",
            event_id=0,
            occurrence_date=today,
            target_chat_id=0,
        )
        if _can_attempt(log, now_utc):
            if digest_events:
                await _deliver(
                    bot,
                    session,
                    log,
                    chat_id=user.tg_id,
                    text=digest_text(user.locale, digest_events),
                    now_utc=now_utc,
                )
            else:
                await _skip(session, log)

    if user.group_enabled:
        for event in events:
            if not event.notify_group or event.target_chat_id is None:
                continue
            log = await _get_or_create_log(
                session,
                owner_id=user.id,
                event_type="group_congrats",
                event_id=event.id,
                occurrence_date=today,
                target_chat_id=event.target_chat_id,
            )
            if _can_attempt(log, now_utc):
                await _deliver(
                    bot,
                    session,
                    log,
                    chat_id=event.target_chat_id,
                    text=group_text(user.locale, event),
                    now_utc=now_utc,
                )

    if user.dm_enabled and user.reminders_enabled and user.reminder_days_before > 0:
        reminder_date = today + timedelta(days=user.reminder_days_before)
        reminder_events = [
            event for event in events_on(sources, reminder_date) if event.notify_digest
        ]
        log = await _get_or_create_log(
            session,
            owner_id=user.id,
            event_type="reminder",
            event_id=0,
            occurrence_date=today,
            target_chat_id=0,
        )
        if _can_attempt(log, now_utc):
            if reminder_events:
                await _deliver(
                    bot,
                    session,
                    log,
                    chat_id=user.tg_id,
                    text=reminder_text(user.locale, reminder_events, user.reminder_days_before),
                    now_utc=now_utc,
                )
            else:
                await _skip(session, log)


async def run_tick(bot: Bot) -> None:
    async with session_scope() as session:
        user_ids = list(await session.scalars(select(User.id)))

    for user_id in user_ids:
        try:
            async with session_scope() as session:
                user = await session.get(User, user_id)
                if user is None:
                    continue
                await run_user(bot, session, user)
        except Exception:
            logger.exception("notification tick failed for user {}", user_id)
