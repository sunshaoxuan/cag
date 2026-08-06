from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


APP_NAME = "agent-gateway"
APP_VERSION = "0.23.0"
DEFAULT_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_GATEWAY_",
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    process_role: str = Field(default="api", pattern=r"^(api|worker|combined)$")
    database_url: str = (
        "postgresql+psycopg://agent_gateway@127.0.0.1:5432/agent_gateway"
    )
    allow_sqlite_for_tests: bool = False
    redis_url: str = "redis://127.0.0.1:6379/0"
    queue_enabled: bool = True
    queue_redis_enabled: bool = True
    queue_redis_channel_prefix: str = "cag:queue"
    queue_interactive_workers: int = Field(default=2, ge=1, le=32)
    queue_knowledge_workers: int = Field(default=1, ge=1, le=8)
    queue_operations_workers: int = Field(default=1, ge=1, le=8)
    queue_poll_seconds: float = Field(default=1.0, ge=0.1, le=30)
    queue_lease_seconds: int = Field(default=120, ge=30, le=3_600)
    queue_heartbeat_seconds: int = Field(default=1, ge=1, le=300)
    queue_shutdown_seconds: int = Field(default=30, ge=1, le=300)
    auto_migrate_legacy_sqlite: bool = True
    legacy_sqlite_path: Path = (
        DEFAULT_REPOSITORY_ROOT
        / "workspaces"
        / ".gateway"
        / "agent_gateway.db"
    )
    migration_receipt_root: Path = (
        DEFAULT_REPOSITORY_ROOT / "backups" / "knowledge-migrations"
    )
    runtime_provider: str = "fake"
    fake_runtime_delay_ms: int = Field(default=25, ge=0, le=60_000)
    sse_poll_interval_ms: int = Field(default=100, ge=10, le=10_000)
    log_level: str = "INFO"
    auto_create_schema: bool = False
    codex_executable: Path | None = None
    codex_startup_timeout_seconds: int = Field(default=30, ge=5, le=300)
    codex_turn_timeout_seconds: int = Field(default=900, ge=30, le=7_200)
    # True keeps the legacy ChatGPT-only policy. The managed host runner sets
    # this to false so local Codex may use either ChatGPT or API-key auth.
    codex_require_chatgpt_auth: bool = False
    harness_max_parallel_agents: int = Field(default=3, ge=1, le=8)
    harness_agent_timeout_seconds: int = Field(default=900, ge=30, le=7_200)
    approval_timeout_seconds: int = Field(default=300, ge=1, le=3_600)
    self_improvement_root: Path | None = None
    operations_admin_token: SecretStr | None = None
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
    knowledge_candidate_limit: int = Field(default=40, ge=10, le=200)
    knowledge_fast_timeout_seconds: int = Field(default=3, ge=1, le=30)
    knowledge_balanced_timeout_seconds: int = Field(default=15, ge=2, le=120)
    knowledge_deep_timeout_seconds: int = Field(default=30, ge=5, le=300)
    knowledge_statement_timeout_ms: int = Field(default=5_000, ge=100, le=60_000)
    knowledge_sources_dir: Path = (
        DEFAULT_REPOSITORY_ROOT / ".gateway" / "knowledge-sources"
    )
    knowledge_rejection_archive_dir: Path = (
        DEFAULT_REPOSITORY_ROOT / ".gateway" / "knowledge-rejection-archives"
    )
    knowledge_rejection_db_retention_days: int = Field(
        default=90, ge=1, le=3_650
    )
    knowledge_rejection_archive_retention_days: int = Field(
        default=365, ge=30, le=3_650
    )
    knowledge_max_file_bytes: int = Field(
        default=10_000_000, ge=1_024, le=100_000_000
    )
    knowledge_max_spreadsheet_cells: int = Field(
        default=250_000, ge=1_000, le=2_000_000
    )
    knowledge_scheduler_enabled: bool = True
    knowledge_scheduler_poll_seconds: int = Field(
        default=10, ge=1, le=3_600
    )
    knowledge_scheduler_lease_seconds: int = Field(
        default=900, ge=30, le=7_200
    )
    svn_executable: str = "svn"
    projects_dir: Path = DEFAULT_REPOSITORY_ROOT / "projects"
    workspace_root: Path = DEFAULT_REPOSITORY_ROOT / "workspaces"
    git_executable: str = "git"
    workspace_prepare_timeout_seconds: int = Field(default=120, ge=5, le=3_600)


@lru_cache
def get_settings() -> Settings:
    return Settings()
