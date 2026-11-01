from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    locale: Mapped[str] = mapped_column(String(8), default="ru", server_default="ru")
    timezone: Mapped[str] = mapped_column(
        String(64), default="Europe/Minsk", server_default="Europe/Minsk"
    )
    digest_time: Mapped[str] = mapped_column(String(5), default="09:00", server_default="09:00")
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    reminder_days_before: Mapped[int] = mapped_column(Integer, default=3, server_default=text("3"))
    dm_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    group_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    chats: Mapped[list[Chat]] = orm_relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    contacts: Mapped[list[Contact]] = orm_relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    anniversaries: Mapped[list[Anniversary]] = orm_relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )


class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = (UniqueConstraint("owner_id", "tg_chat_id", name="uq_chats_owner_chat"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tg_chat_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[str | None] = mapped_column(String(32))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    owner: Mapped[User] = orm_relationship(back_populates="chats")


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("chat_id", "tg_user_id", name="uq_group_members"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger)
    full_name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(64))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        Index("ix_contacts_owner_md", "owner_id", "month", "day"),
        Index("ix_contacts_owner_active", "owner_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    day: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    birth_year: Mapped[int | None] = mapped_column(Integer)
    relationship: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)
    target_chat_id: Mapped[int | None] = mapped_column(ForeignKey("chats.id", ondelete="SET NULL"))
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    notify_digest: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    notify_group: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    notify_direct: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    owner: Mapped[User] = orm_relationship(back_populates="contacts")
    target_chat: Mapped[Chat | None] = orm_relationship()


class Anniversary(Base):
    __tablename__ = "anniversaries"
    __table_args__ = (
        Index("ix_anniversaries_owner_md", "owner_id", "month", "day"),
        Index("ix_anniversaries_owner_active", "owner_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    day: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    start_year: Mapped[int | None] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16), default="custom", server_default="custom")
    recurring: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    notes: Mapped[str | None] = mapped_column(Text)
    target_chat_id: Mapped[int | None] = mapped_column(ForeignKey("chats.id", ondelete="SET NULL"))
    notify_digest: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    notify_group: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    notify_direct: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    owner: Mapped[User] = orm_relationship(back_populates="anniversaries")
    target_chat: Mapped[Chat | None] = orm_relationship()


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "event_type",
            "event_id",
            "occurrence_date",
            "target_chat_id",
            name="uq_notification_once",
        ),
        Index("ix_notification_owner_date", "owner_id", "occurrence_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    event_id: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    occurrence_date: Mapped[Date] = mapped_column(Date)
    target_chat_id: Mapped[int] = mapped_column(BigInteger, default=0, server_default=text("0"))
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
