from __future__ import annotations

from alembic import command
from alembic.config import Config

from dobby.config import PROJECT_ROOT, get_settings


def upgrade_to_head() -> None:
    settings = get_settings()
    settings.ensure_dirs()

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", settings.sync_database_url)
    command.upgrade(config, "head")
