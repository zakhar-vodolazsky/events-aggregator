from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def normalize_database_url(value: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if value.startswith(prefix):
            return "postgresql+asyncpg://" + value[len(prefix) :]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    database_url: Annotated[str, BeforeValidator(normalize_database_url)] = Field(
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_CONNECTION_STRING")
    )
    events_provider_api_key: str = Field(validation_alias="EVENTS_API_KEY")
    events_provider_base_url: str = Field(validation_alias="EVENTS_API_URL")
    sync_enabled: bool = True
    sync_interval_seconds: int = Field(default=86400, ge=60)


@lru_cache
def get_settings() -> Settings:
    # noinspection PyArgumentList
    return Settings()
