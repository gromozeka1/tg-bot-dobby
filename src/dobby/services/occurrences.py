from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.db.models import Anniversary, Chat, Contact, User
from dobby.services.dates import Occurrence, age_on, is_event_on, years_since


@dataclass(slots=True)
class EventSource:
    kind: str
    id: int
    title: str
    day: int
    month: int
    year: int | None
    recurring: bool
    notify_digest: bool
    notify_group: bool
    notify_direct: bool
    target_chat_id: int | None
    telegram_username: str | None = None
    telegram_user_id: int | None = None
    subkind: str | None = None

    def occurs_on(self, on_date: date) -> bool:
        if not is_event_on(self.day, self.month, on_date):
            return False
        if self.kind == "anniversary" and not self.recurring:
            return self.year == on_date.year
        return True

    def to_occurrence(self, on_date: date) -> Occurrence:
        years = (
            age_on(self.year, on_date)
            if self.kind == "birthday"
            else years_since(self.year, on_date)
        )
        return Occurrence(
            kind=self.kind,
            id=self.id,
            title=self.title,
            date=on_date,
            years=years,
            notify_digest=self.notify_digest,
            notify_group=self.notify_group,
            notify_direct=self.notify_direct,
            target_chat_id=self.target_chat_id,
            telegram_username=self.telegram_username,
            telegram_user_id=self.telegram_user_id,
            subkind=self.subkind,
        )


async def load_sources(session: AsyncSession, user: User) -> list[EventSource]:
    chats = (
        await session.scalars(select(Chat).where(Chat.owner_id == user.id))
    ).all()
    chat_by_id = {chat.id: chat.tg_chat_id for chat in chats}
    default_chat = next((chat for chat in chats if chat.is_default), chats[0] if chats else None)
    default_tg_id = default_chat.tg_chat_id if default_chat else None

    contacts = (
        await session.scalars(
            select(Contact).where(Contact.owner_id == user.id, Contact.is_active.is_(True))
        )
    ).all()
    anniversaries = (
        await session.scalars(
            select(Anniversary).where(
                Anniversary.owner_id == user.id, Anniversary.is_active.is_(True)
            )
        )
    ).all()

    sources: list[EventSource] = []
    for contact in contacts:
        target = (
            chat_by_id.get(contact.target_chat_id)
            if contact.target_chat_id is not None
            else None
        )
        sources.append(
            EventSource(
                kind="birthday",
                id=contact.id,
                title=contact.full_name,
                day=contact.day,
                month=contact.month,
                year=contact.birth_year,
                recurring=True,
                notify_digest=contact.notify_digest,
                notify_group=contact.notify_group,
                notify_direct=contact.notify_direct,
                target_chat_id=target or default_tg_id,
                telegram_username=contact.telegram_username,
                telegram_user_id=contact.telegram_user_id,
            )
        )

    for item in anniversaries:
        target = (
            chat_by_id.get(item.target_chat_id) if item.target_chat_id is not None else None
        )
        sources.append(
            EventSource(
                kind="anniversary",
                id=item.id,
                title=item.title,
                day=item.day,
                month=item.month,
                year=item.start_year,
                recurring=item.recurring,
                notify_digest=item.notify_digest,
                notify_group=item.notify_group,
                notify_direct=item.notify_direct,
                target_chat_id=target or default_tg_id,
                subkind=item.kind,
            )
        )
    return sources


def events_on(sources: list[EventSource], on_date: date) -> list[Occurrence]:
    events = [source.to_occurrence(on_date) for source in sources if source.occurs_on(on_date)]
    events.sort(key=lambda event: (event.kind != "birthday", event.title.lower()))
    return events


def upcoming(
    sources: list[EventSource], start: date, days: int = 14
) -> list[tuple[date, list[Occurrence]]]:
    result: list[tuple[date, list[Occurrence]]] = []
    for offset in range(days + 1):
        current = start + timedelta(days=offset)
        day_events = events_on(sources, current)
        if day_events:
            result.append((current, day_events))
    return result
