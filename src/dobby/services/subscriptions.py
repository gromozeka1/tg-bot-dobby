from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.db.models import Anniversary, Contact

CHANNEL_FIELDS = {
    "digest": "notify_digest",
    "group": "notify_group",
    "direct": "notify_direct",
}
FILTERS = ("all", "birthdays", "anniversaries", "muted")


@dataclass(slots=True)
class SubItem:
    kind: str
    id: int
    title: str
    day: int
    month: int
    notify_digest: bool
    notify_group: bool
    notify_direct: bool

    @property
    def muted(self) -> bool:
        return not (self.notify_digest or self.notify_group or self.notify_direct)


def _from_contact(contact: Contact) -> SubItem:
    return SubItem(
        kind="birthday",
        id=contact.id,
        title=contact.full_name,
        day=contact.day,
        month=contact.month,
        notify_digest=contact.notify_digest,
        notify_group=contact.notify_group,
        notify_direct=contact.notify_direct,
    )


def _from_anniversary(item: Anniversary) -> SubItem:
    return SubItem(
        kind="anniversary",
        id=item.id,
        title=item.title,
        day=item.day,
        month=item.month,
        notify_digest=item.notify_digest,
        notify_group=item.notify_group,
        notify_direct=item.notify_direct,
    )


async def list_items(
    session: AsyncSession, owner_id: int, filter_name: str = "all"
) -> list[SubItem]:
    contacts = (
        await session.scalars(
            select(Contact).where(Contact.owner_id == owner_id, Contact.is_active.is_(True))
        )
    ).all()
    anniversaries = (
        await session.scalars(
            select(Anniversary).where(
                Anniversary.owner_id == owner_id, Anniversary.is_active.is_(True)
            )
        )
    ).all()

    items = [_from_contact(contact) for contact in contacts]
    items += [_from_anniversary(item) for item in anniversaries]
    items.sort(key=lambda item: (item.month, item.day, item.title.lower()))

    if filter_name == "birthdays":
        items = [item for item in items if item.kind == "birthday"]
    elif filter_name == "anniversaries":
        items = [item for item in items if item.kind == "anniversary"]
    elif filter_name == "muted":
        items = [item for item in items if item.muted]
    return items


async def get_item(
    session: AsyncSession, owner_id: int, kind: str, item_id: int
) -> Contact | Anniversary | None:
    if kind == "birthday":
        model = Contact
    elif kind == "anniversary":
        model = Anniversary
    else:
        return None
    item = await session.get(model, item_id)
    if item is None or item.owner_id != owner_id:
        return None
    return item


async def toggle_channel(
    session: AsyncSession, owner_id: int, kind: str, item_id: int, channel: str
) -> bool | None:
    if channel not in CHANNEL_FIELDS:
        return None
    item = await get_item(session, owner_id, kind, item_id)
    if item is None:
        return None
    field = CHANNEL_FIELDS[channel]
    value = not getattr(item, field)
    setattr(item, field, value)
    await session.flush()
    return value


async def bulk_mute(session: AsyncSession, owner_id: int, kind: str, *, mute: bool) -> None:
    value = not mute
    models = []
    if kind in ("all", "birthday"):
        models.append(Contact)
    if kind in ("all", "anniversary"):
        models.append(Anniversary)
    for model in models:
        await session.execute(
            update(model)
            .where(model.owner_id == owner_id)
            .values(
                notify_digest=value,
                notify_group=value,
                notify_direct=value,
            )
        )
    await session.flush()
