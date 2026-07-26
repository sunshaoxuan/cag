from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


APP_NAME = "agent-gateway"
APP_VERSION = "0.1.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_GATEWAY_",
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "sqlite+pysqlite:///./agent_gateway.db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    runtime_provider: str = "fake"
    fake_runtime_delay_ms: int = Field(default=25, ge=0, le=60_000)
    sse_poll_interval_ms: int = Field(default=100, ge=10, le=10_000)
    log_level: str = "INFO"
    auto_create_schema: bool = True
    codex_executable: Path | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
