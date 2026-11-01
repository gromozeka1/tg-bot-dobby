from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.db.models import Anniversary

CHANNEL_FIELDS = {
    "digest": "notify_digest",
    "group": "notify_group",
    "direct": "notify_direct",
}


async def list_anniversaries(
    session: AsyncSession, owner_id: int, page: int = 0, per_page: int = 5
) -> tuple[list[Anniversary], int]:
    total = await session.scalar(
        select(func.count(Anniversary.id)).where(
            Anniversary.owner_id == owner_id, Anniversary.is_active.is_(True)
        )
    )
    total = int(total or 0)
    page = max(0, min(page, max(0, (total - 1) // per_page)))
    items = (
        await session.scalars(
            select(Anniversary)
            .where(Anniversary.owner_id == owner_id, Anniversary.is_active.is_(True))
            .order_by(Anniversary.month, Anniversary.day, Anniversary.title)
            .offset(page * per_page)
            .limit(per_page)
        )
    ).all()
    return list(items), total


async def get_anniversary(
    session: AsyncSession, owner_id: int, anniversary_id: int
) -> Anniversary | None:
    item = await session.get(Anniversary, anniversary_id)
    if item is None or item.owner_id != owner_id:
        return None
    return item


async def create_anniversary(
    session: AsyncSession,
    owner_id: int,
    *,
    title: str,
    day: int,
    month: int,
    start_year: int | None,
    kind: str = "custom",
    recurring: bool = True,
    target_chat_id: int | None = None,
    notify_group: bool = True,
) -> Anniversary:
    item = Anniversary(
        owner_id=owner_id,
        title=title.strip()[:255],
        day=day,
        month=month,
        start_year=start_year,
        kind=kind,
        recurring=recurring,
        target_chat_id=target_chat_id,
        notify_group=notify_group,
    )
    session.add(item)
    await session.flush()
    return item


async def delete_anniversary(session: AsyncSession, item: Anniversary) -> None:
    await session.delete(item)
    await session.flush()


async def toggle_anniversary_channel(
    session: AsyncSession, item: Anniversary, channel: str
) -> bool:
    field = CHANNEL_FIELDS[channel]
    value = not getattr(item, field)
    setattr(item, field, value)
    await session.flush()
    return value


async def set_anniversary_channels(
    session: AsyncSession, item: Anniversary, *, digest: bool, group: bool, direct: bool
) -> None:
    item.notify_digest = digest
    item.notify_group = group
    item.notify_direct = direct
    await session.flush()
