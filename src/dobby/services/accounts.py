from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dobby.db.models import Anniversary, Chat, Contact, GroupMember, NotificationLog, User


async def delete_account(session: AsyncSession, user_id: int) -> None:
    chat_ids = select(Chat.id).where(Chat.owner_id == user_id)
    await session.execute(delete(GroupMember).where(GroupMember.chat_id.in_(chat_ids)))
    await session.execute(delete(NotificationLog).where(NotificationLog.owner_id == user_id))
    await session.execute(delete(Contact).where(Contact.owner_id == user_id))
    await session.execute(delete(Anniversary).where(Anniversary.owner_id == user_id))
    await session.execute(delete(Chat).where(Chat.owner_id == user_id))
    await session.execute(delete(User).where(User.id == user_id))
