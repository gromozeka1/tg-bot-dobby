from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from loguru import logger

from dobby.bot.dispatcher import create_dispatcher
from dobby.config import get_settings
from dobby.db.migrate import upgrade_to_head
from dobby.i18n import compile_catalogs
from dobby.logging import setup_logging
from dobby.scheduler import create_scheduler
from dobby.utils.lock import InstanceLock


async def register_commands(bot: Bot) -> None:
    private = [
        BotCommand(command="today", description="Today's events"),
        BotCommand(command="upcoming", description="Next 14 days"),
        BotCommand(command="contacts", description="Contact list"),
        BotCommand(command="addcontact", description="Add a contact"),
        BotCommand(command="anniversaries", description="Anniversary list"),
        BotCommand(command="addanniversary", description="Add an anniversary"),
        BotCommand(command="subscriptions", description="Digest and group settings"),
        BotCommand(command="settings", description="Time, reminders, language"),
        BotCommand(command="id", description="Show my Telegram ID"),
        BotCommand(command="help", description="Help"),
    ]
    try:
        await bot.set_my_commands(private, scope=BotCommandScopeAllPrivateChats())
        await bot.delete_my_commands(scope=BotCommandScopeAllGroupChats())
        await bot.delete_my_commands()
    except TelegramAPIError as exc:
        logger.warning("Could not register bot commands: {}", exc)


async def run(token: str) -> None:
    upgrade_to_head()

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await register_commands(bot)
    dispatcher = create_dispatcher()
    scheduler = create_scheduler(bot)
    scheduler.start()

    logger.info("Dobby is starting (polling)")
    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Dobby stopped")


def main() -> None:
    settings = get_settings()
    setup_logging()
    compile_catalogs()

    token = settings.token
    if not token:
        logger.error("BOT_TOKEN is empty. Copy .env.example to .env and paste the token.")
        raise SystemExit(2)

    lock = InstanceLock(settings.data_dir / "dobby.lock")
    if not lock.acquire():
        logger.error("Another Dobby instance is already running.")
        raise SystemExit(3)

    try:
        asyncio.run(run(token))
    except KeyboardInterrupt:
        logger.info("Interrupted")


if __name__ == "__main__":
    main()
