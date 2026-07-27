from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


APP_NAME = "agent-gateway"
APP_VERSION = "0.7.1"
DEFAULT_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


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
    codex_startup_timeout_seconds: int = Field(default=30, ge=5, le=300)
    codex_turn_timeout_seconds: int = Field(default=900, ge=30, le=7_200)
    codex_require_chatgpt_auth: bool = True
    harness_max_parallel_agents: int = Field(default=3, ge=1, le=8)
    harness_agent_timeout_seconds: int = Field(default=900, ge=30, le=7_200)
    approval_timeout_seconds: int = Field(default=300, ge=1, le=3_600)
    self_improvement_root: Path | None = None
    knowledge_enabled: bool = False
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_embedding_model: str = "qwen3-embedding:8b"
    ollama_memory_model: str = "qwen3:14b"
    ollama_embedding_dimensions: int = Field(default=1024, ge=32, le=4096)
    ollama_timeout_seconds: int = Field(default=120, ge=5, le=900)
    knowledge_allowed_roots: str = ""
    knowledge_encryption_key: str | None = None
    knowledge_keyring_service: str = "agent-gateway"
    knowledge_keyring_username: str = "enterprise-knowledge"
    knowledge_max_context_chars: int = Field(default=12_000, ge=1_000, le=100_000)
    knowledge_max_chunks: int = Field(default=8, ge=1, le=50)
    projects_dir: Path = DEFAULT_REPOSITORY_ROOT / "projects"
    workspace_root: Path = DEFAULT_REPOSITORY_ROOT / "workspaces"
    git_executable: str = "git"
    workspace_prepare_timeout_seconds: int = Field(default=120, ge=5, le=3_600)


@lru_cache
def get_settings() -> Settings:
    return Settings()
