from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: SecretStr = SecretStr("")
    admin_tg_id: int | None = None
    database_url: str = "sqlite+aiosqlite:///./data/dobby.sqlite3"
    default_locale: str = "ru"
    default_tz: str = "Europe/Minsk"
    default_digest_time: str = "09:00"
    log_level: str = "INFO"

    @field_validator("admin_tg_id", mode="before")
    @classmethod
    def _empty_admin_to_none(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value

    @property
    def token(self) -> str:
        return self.bot_token.get_secret_value().strip()

    @property
    def data_dir(self) -> Path:
        return PROJECT_ROOT / "data"

    @property
    def logs_dir(self) -> Path:
        return PROJECT_ROOT / "logs"

    @property
    def backups_dir(self) -> Path:
        return PROJECT_ROOT / "backups"

    @property
    def resolved_database_url(self) -> str:
        prefix = "sqlite+aiosqlite:///./"
        if self.database_url.startswith(prefix):
            relative = self.database_url[len(prefix) :]
            return f"sqlite+aiosqlite:///{(PROJECT_ROOT / relative).as_posix()}"
        return self.database_url

    @property
    def sync_database_url(self) -> str:
        return self.resolved_database_url.replace("+aiosqlite", "")

    def ensure_dirs(self) -> None:
        for directory in (self.data_dir, self.logs_dir, self.backups_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
