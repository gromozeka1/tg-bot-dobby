from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.db.models import Chat, Contact, GroupMember, User
from dobby.services import contacts as contacts_service
from dobby.utils.parsing import ParsedDate, ParseError, validate_birth_date

RECHECK_AFTER = timedelta(days=7)

BirthdayFetcher = Callable[[], Awaitable[tuple[int, int, int | None] | None]]


@dataclass(frozen=True, slots=True)
class ImportedContact:
    owner: User
    chat: Chat
    contact: Contact


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def track_member(
    session: AsyncSession,
    *,
    tg_chat_id: int,
    tg_user_id: int,
    full_name: str,
    username: str | None,
    fetch_birthday: BirthdayFetcher,
    now: datetime | None = None,
) -> list[ImportedContact]:
    """Remember a group member and import them as a contact once their birthday is known."""
    now = now or datetime.now(UTC)
    chats = list(await session.scalars(select(Chat).where(Chat.tg_chat_id == tg_chat_id)))
    imported: list[ImportedContact] = []
    birthday: tuple[int, int, int | None] | None = None
    fetched = False

    for chat in chats:
        member = await session.scalar(
            select(GroupMember).where(
                GroupMember.chat_id == chat.id, GroupMember.tg_user_id == tg_user_id
            )
        )
        if member is None:
            member = GroupMember(chat_id=chat.id, tg_user_id=tg_user_id, full_name=full_name)
            session.add(member)
        member.full_name = full_name[:255]
        member.username = username
        if member.imported_at is not None:
            continue
        if member.last_checked_at and now - _aware(member.last_checked_at) < RECHECK_AFTER:
            continue

        if not fetched:
            birthday = await fetch_birthday()
            if birthday is not None:
                try:
                    validate_birth_date(ParsedDate(*birthday))
                except ParseError:
                    birthday = None
            fetched = True
        member.last_checked_at = now
        if birthday is None:
            continue

        owner = await session.get(User, chat.owner_id)
        if owner is None:
            continue
        member.imported_at = now
        known = await session.scalar(
            select(Contact.id).where(
                Contact.owner_id == owner.id, Contact.telegram_user_id == tg_user_id
            )
        )
        if known is not None:
            continue
        day, month, year = birthday
        contact = await contacts_service.create_contact(
            session,
            owner.id,
            full_name=full_name,
            day=day,
            month=month,
            birth_year=year,
            target_chat_id=chat.id,
            telegram_user_id=tg_user_id,
        )
        contact.telegram_username = username
        imported.append(ImportedContact(owner=owner, chat=chat, contact=contact))

    await session.flush()
    return imported
