from __future__ import annotations

from aiogram.types import User as TelegramUser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.config import get_settings
from dobby.db.models import Contact, User

CHANNEL_FIELDS = {
    "digest": "notify_digest",
    "group": "notify_group",
    "direct": "notify_direct",
}


async def get_or_create_user(session: AsyncSession, tg_user: TelegramUser) -> User:
    settings = get_settings()
    user = await session.scalar(select(User).where(User.tg_id == tg_user.id))
    if user is None:
        user = User(
            tg_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            locale=settings.default_locale,
            timezone=settings.default_tz,
            digest_time=settings.default_digest_time,
        )
        session.add(user)
        await session.flush()
    else:
        if user.username != tg_user.username:
            user.username = tg_user.username
        if user.first_name != tg_user.first_name:
            user.first_name = tg_user.first_name
    return user


async def list_contacts(
    session: AsyncSession, owner_id: int, page: int = 0, per_page: int = 5
) -> tuple[list[Contact], int]:
    total = await session.scalar(
        select(func.count(Contact.id)).where(
            Contact.owner_id == owner_id, Contact.is_active.is_(True)
        )
    )
    total = int(total or 0)
    page = max(0, min(page, max(0, (total - 1) // per_page)))
    contacts = (
        await session.scalars(
            select(Contact)
            .where(Contact.owner_id == owner_id, Contact.is_active.is_(True))
            .order_by(Contact.month, Contact.day, Contact.full_name)
            .offset(page * per_page)
            .limit(per_page)
        )
    ).all()
    return list(contacts), total


async def get_contact(session: AsyncSession, owner_id: int, contact_id: int) -> Contact | None:
    contact = await session.get(Contact, contact_id)
    if contact is None or contact.owner_id != owner_id:
        return None
    return contact


async def create_contact(
    session: AsyncSession,
    owner_id: int,
    *,
    full_name: str,
    day: int,
    month: int,
    birth_year: int | None,
    relationship: str | None = None,
    target_chat_id: int | None = None,
    notify_group: bool = True,
    telegram_user_id: int | None = None,
) -> Contact:
    contact = Contact(
        telegram_user_id=telegram_user_id,
        owner_id=owner_id,
        full_name=full_name.strip()[:255],
        day=day,
        month=month,
        birth_year=birth_year,
        relationship=relationship,
        target_chat_id=target_chat_id,
        notify_group=notify_group,
    )
    session.add(contact)
    await session.flush()
    return contact


async def delete_contact(session: AsyncSession, contact: Contact) -> None:
    await session.delete(contact)
    await session.flush()


async def toggle_contact_channel(
    session: AsyncSession, contact: Contact, channel: str
) -> bool:
    field = CHANNEL_FIELDS[channel]
    value = not getattr(contact, field)
    setattr(contact, field, value)
    await session.flush()
    return value


async def set_contact_channels(
    session: AsyncSession, contact: Contact, *, digest: bool, group: bool, direct: bool
) -> None:
    contact.notify_digest = digest
    contact.notify_group = group
    contact.notify_direct = direct
    await session.flush()
