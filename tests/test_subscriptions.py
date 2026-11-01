from __future__ import annotations

from dobby.db.models import Anniversary, Chat, Contact, User
from dobby.services.subscriptions import bulk_mute, list_items, toggle_channel


async def _seed(session):
    user = User(tg_id=1)
    session.add(user)
    await session.flush()

    chat = Chat(owner_id=user.id, tg_chat_id=-100, title="Family", is_default=True)
    session.add(chat)
    await session.flush()

    contact = Contact(owner_id=user.id, full_name="Анна", day=12, month=5)
    anniversary = Anniversary(owner_id=user.id, title="Свадьба", day=1, month=6)
    session.add_all([contact, anniversary])
    await session.flush()
    return user, contact, anniversary


async def test_list_filters(session) -> None:
    user, _contact, _anniversary = await _seed(session)

    assert len(await list_items(session, user.id, "all")) == 2
    assert len(await list_items(session, user.id, "birthdays")) == 1
    assert len(await list_items(session, user.id, "anniversaries")) == 1
    assert await list_items(session, user.id, "muted") == []


async def test_toggle_channel(session) -> None:
    user, contact, _anniversary = await _seed(session)

    for channel in ("digest", "group"):
        value = await toggle_channel(session, user.id, "birthday", contact.id, channel)
        assert value is False
    assert contact.notify_digest is False
    assert contact.notify_group is False
    assert contact.notify_direct is False

    muted = await list_items(session, user.id, "muted")
    assert [item.id for item in muted] == [contact.id]


async def test_bulk_mute(session) -> None:
    user, contact, anniversary = await _seed(session)

    await bulk_mute(session, user.id, "birthday", mute=True)
    assert contact.notify_digest is False
    assert contact.notify_group is False
    assert anniversary.notify_digest is True

    await bulk_mute(session, user.id, "all", mute=True)
    assert anniversary.notify_digest is False

    muted = await list_items(session, user.id, "muted")
    assert len(muted) == 2


async def test_unknown_channel_returns_none(session) -> None:
    user, contact, _anniversary = await _seed(session)
    assert await toggle_channel(session, user.id, "birthday", contact.id, "nope") is None
    assert await toggle_channel(session, user.id, "unknown", contact.id, "digest") is None
