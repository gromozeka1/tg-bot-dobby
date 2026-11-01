from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from dobby.db.models import Chat, Contact, GroupMember, User
from dobby.services.members import RECHECK_AFTER, track_member

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


async def _setup(session) -> Chat:
    owner = User(tg_id=1)
    session.add(owner)
    await session.flush()
    chat = Chat(owner_id=owner.id, tg_chat_id=-100, title="Team")
    session.add(chat)
    await session.flush()
    return chat


def _fetcher(value, calls: list[int]):
    async def fetch():
        calls.append(1)
        return value

    return fetch


async def _track(session, fetch, now=NOW, user_id=42):
    return await track_member(
        session,
        tg_chat_id=-100,
        tg_user_id=user_id,
        full_name="Anna",
        username="anna",
        fetch_birthday=fetch,
        now=now,
    )


async def test_imports_contact_when_birthday_known(session) -> None:
    chat = await _setup(session)
    imported = await _track(session, _fetcher((12, 5, 1990), []))
    assert len(imported) == 1
    contact = await session.scalar(select(Contact))
    assert (contact.day, contact.month, contact.birth_year) == (12, 5, 1990)
    assert contact.telegram_user_id == 42
    assert contact.target_chat_id == chat.id

    # imported members are never imported twice, even if the contact is deleted
    await session.delete(contact)
    await session.flush()
    assert await _track(session, _fetcher((12, 5, 1990), []), now=NOW + timedelta(days=30)) == []
    assert await session.scalar(select(func.count(Contact.id))) == 0


async def test_unknown_birthday_is_rechecked_weekly(session) -> None:
    await _setup(session)
    calls: list[int] = []
    assert await _track(session, _fetcher(None, calls)) == []
    assert await _track(session, _fetcher(None, calls), now=NOW + timedelta(days=1)) == []
    assert len(calls) == 1
    assert await session.scalar(select(func.count(GroupMember.id))) == 1

    later = NOW + RECHECK_AFTER + timedelta(minutes=1)
    imported = await _track(session, _fetcher((1, 2, None), calls), now=later)
    assert len(imported) == 1
    assert len(calls) == 2


async def test_existing_contact_is_not_duplicated(session) -> None:
    chat = await _setup(session)
    session.add(
        Contact(owner_id=chat.owner_id, full_name="Anna", day=1, month=1, telegram_user_id=42)
    )
    await session.flush()
    assert await _track(session, _fetcher((12, 5, None), [])) == []
    assert await session.scalar(select(func.count(Contact.id))) == 1


async def test_unbound_group_is_ignored(session) -> None:
    calls: list[int] = []
    assert await _track(session, _fetcher((12, 5, None), calls)) == []
    assert calls == []
