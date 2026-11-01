from __future__ import annotations

from aiogram.filters import Filter
from aiogram.types import Message


class MenuButton(Filter):
    """Match a reply-keyboard button using the current locale's translation."""

    def __init__(self, key: str) -> None:
        self.key = key

    async def __call__(self, message: Message, **data: object) -> bool:
        translate = data.get("_")
        if not callable(translate) or not message.text:
            return False
        return message.text == translate(self.key)
