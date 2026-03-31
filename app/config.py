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
    encryption_key: str | None = None
    slack_client_id: str | None = None
    slack_client_secret: str | None = None
    slack_redirect_uri: str | None = None
    oauth_state_ttl_seconds: int = 600
    celery_task_time_limit: int = 600  # 10 min hard kill per task

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
settings = Settings()
