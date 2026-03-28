from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "Context Engine"
    environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/context_engine"
    )
    redis_url: str = "redis://localhost:6379/0"
    litellm_api_key: str | None = None
    cohere_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
settings = Settings()
