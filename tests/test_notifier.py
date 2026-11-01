from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from dobby.db.models import Chat, Contact, NotificationLog, User
from dobby.services.notifier import run_user
from tests.conftest import FakeBot

NOW = datetime(2026, 5, 15, 6, 0, tzinfo=UTC)  # 09:00 in Minsk


async def _seed(session, *, day: int = 15, month: int = 5, **contact_kwargs):
    user = User(tg_id=1, timezone="Europe/Minsk", digest_time="09:00")
    session.add(user)
    await session.flush()

    chat = Chat(
        owner_id=user.id,
        tg_chat_id=-100,
        title="Family",
        type="group",
        is_default=True,
    )
    session.add(chat)
    await session.flush()

    contact = Contact(
        owner_id=user.id,
        full_name="Анна",
        day=day,
        month=month,
        birth_year=1990,
        **contact_kwargs,
    )
    session.add(contact)
    await session.flush()
    return user, chat, contact


async def test_digest_and_group_congrats_sent_once(session) -> None:
    user, _chat, _contact = await _seed(session)
    bot = FakeBot()

    await run_user(bot, session, user, NOW)

    assert len(bot.messages) == 2
    assert bot.messages[0][0] == 1
    assert "Анна" in bot.messages[0][1]
    assert "36" in bot.messages[0][1]
    assert bot.messages[1][0] == -100
    assert "С днём рождения" in bot.messages[1][1]

    await run_user(bot, session, user, NOW)
    assert len(bot.messages) == 2


async def test_muted_contact_sends_nothing(session) -> None:
    user, _chat, _contact = await _seed(session, notify_digest=False, notify_group=False)
    bot = FakeBot()

    await run_user(bot, session, user, NOW)

    assert bot.messages == []
    logs = list(await session.scalars(select(NotificationLog)))
    assert logs and all(log.status == "skipped" for log in logs)


async def test_skipped_digest_can_send_after_event_is_added(session) -> None:
    user = User(tg_id=1, timezone="Europe/Minsk", digest_time="09:00")
    session.add(user)
    await session.flush()
    bot = FakeBot()

    await run_user(bot, session, user, NOW)
    assert bot.messages == []

    contact = Contact(owner_id=user.id, full_name="Анна", day=15, month=5)
    session.add(contact)
    await session.flush()
    await run_user(bot, session, user, NOW + timedelta(minutes=1))

    assert len(bot.messages) == 1
    assert bot.messages[0][0] == user.tg_id


async def test_reminder_three_days_before(session) -> None:
    user, _chat, _contact = await _seed(session, day=18)
    bot = FakeBot()

    await run_user(bot, session, user, NOW)

    assert len(bot.messages) == 1
    assert bot.messages[0][0] == 1
    assert "Через 3 дня" in bot.messages[0][1]
    assert "Анна" in bot.messages[0][1]

    await run_user(bot, session, user, NOW)
    assert len(bot.messages) == 1


async def test_reminder_global_toggle_off(session) -> None:
    user, _chat, _contact = await _seed(session, day=18)
    user.reminders_enabled = False
    await session.flush()
    bot = FakeBot()

    await run_user(bot, session, user, NOW)

    assert bot.messages == []


async def test_reminder_respects_dm_toggle(session) -> None:
    user, _chat, _contact = await _seed(session, day=18)
    user.dm_enabled = False
    await session.flush()
    bot = FakeBot()

    await run_user(bot, session, user, NOW)

    assert bot.messages == []


async def test_group_toggle_off_sends_only_digest(session) -> None:
    user, _chat, _contact = await _seed(session)
    user.group_enabled = False
    await session.flush()
    bot = FakeBot()

    await run_user(bot, session, user, NOW)

    assert len(bot.messages) == 1
    assert bot.messages[0][0] == 1


async def test_before_digest_time_does_nothing(session) -> None:
    user, _chat, _contact = await _seed(session)
    bot = FakeBot()

    await run_user(bot, session, user, datetime(2026, 5, 15, 5, 0, tzinfo=UTC))

    assert bot.messages == []


async def test_failed_delivery_retries_after_ten_minutes(session) -> None:
    user, _chat, _contact = await _seed(session)

    class FailFirstDmBot(FakeBot):
        failed = False

        async def send_message(self, chat_id: int, text: str, **kwargs):
            if chat_id == user.tg_id and not self.failed:
                self.failed = True
                raise RuntimeError("temporary network failure")
            return await super().send_message(chat_id, text, **kwargs)

    bot = FailFirstDmBot()

    await run_user(bot, session, user, NOW)
    dm_attempts = [message for message in bot.messages if message[0] == user.tg_id]
    assert dm_attempts == []

    await run_user(bot, session, user, NOW + timedelta(minutes=9))
    dm_attempts = [message for message in bot.messages if message[0] == user.tg_id]
    assert dm_attempts == []

    await run_user(bot, session, user, NOW + timedelta(minutes=10))
    dm_attempts = [message for message in bot.messages if message[0] == user.tg_id]
    assert len(dm_attempts) == 1
