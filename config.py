from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__name__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / "env.py", env_file_encoding="utf-8", extra="ignore"
    )
    database_url: str = Field(validation_alias="DATABASE_URL")


@lru_cache
def get_settings():
    return Settings
