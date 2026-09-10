from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__name__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    database_url: str = Field(validation_alias="DATABASE_URL")
    events_provider_api_key: str = Field(validation_alias="EVENTS_API_KEY")
    events_provider_base_url: str = Field(validation_alias="EVENTS_API_URL")


@lru_cache
def get_settings():
    # noinspection PyArgumentList
    return Settings()
