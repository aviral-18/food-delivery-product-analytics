"""
Application configuration.

Settings are loaded from environment variables (and an optional `.env` file)
via pydantic-settings. This is the single source of truth for all runtime
configuration — nothing else in the codebase should read `os.environ` directly.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    APP_NAME: str = "Eternal Product Analytics"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ---- Database (PostgreSQL) ----
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/food_delivery_analytics"
    )
    SQL_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # ---- Security / JWT ----
    SECRET_KEY: str = "CHANGE_ME_dev_key_rotate_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- CORS ----
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    # ---- Synthetic data generation ----
    SEED: int = 42
    GEN_CUSTOMERS: int = 30_000
    GEN_RESTAURANTS: int = 2_000
    GEN_PARTNERS: int = 100
    GEN_ORDERS: int = 120_000
    GEN_MONTHS: int = 24

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (import this everywhere)."""
    return Settings()


settings = get_settings()
