from __future__ import annotations

from datetime import date

from sqlalchemy import select

from dobby.db.models import Anniversary, Chat, Contact, NotificationLog, User
from dobby.services.accounts import delete_account


async def test_delete_account_removes_owned_data_only(session) -> None:
    owner = User(tg_id=1)
    other = User(tg_id=2)
    session.add_all([owner, other])
    await session.flush()

    chat = Chat(owner_id=owner.id, tg_chat_id=-100)
    other_contact = Contact(owner_id=other.id, full_name="Other", day=1, month=1)
    session.add_all([chat, other_contact])
    await session.flush()
    contact = Contact(
        owner_id=owner.id,
        full_name="Owner",
        day=2,
        month=2,
        target_chat_id=chat.id,
    )
    anniversary = Anniversary(
        owner_id=owner.id, title="Wedding", day=3, month=3, target_chat_id=chat.id
    )
    log = NotificationLog(
        owner_id=owner.id,
        event_type="digest",
        occurrence_date=date(2026, 3, 3),
    )
    session.add_all([contact, anniversary, log])
    await session.flush()

    await delete_account(session, owner.id)

    assert await session.get(User, owner.id) is None
    assert list(await session.scalars(select(Chat).where(Chat.owner_id == owner.id))) == []
    assert list(await session.scalars(select(Contact).where(Contact.owner_id == owner.id))) == []
    assert (
        list(await session.scalars(select(Anniversary).where(Anniversary.owner_id == owner.id)))
        == []
    )
    assert (
        list(
            await session.scalars(
                select(NotificationLog).where(NotificationLog.owner_id == owner.id)
            )
        )
        == []
    )
    assert await session.get(User, other.id) is not None
    assert await session.get(Contact, other_contact.id) is not None
