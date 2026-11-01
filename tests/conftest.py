from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dobby.db.models import Base
from dobby.i18n import compile_catalogs

compile_catalogs()


class FakeMessage:
    _counter = 0

    def __init__(self) -> None:
        FakeMessage._counter += 1
        self.message_id = FakeMessage._counter


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str, **kwargs) -> FakeMessage:
        self.messages.append((chat_id, text))
        return FakeMessage()


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as db_session:
        yield db_session
    await engine.dispose()
