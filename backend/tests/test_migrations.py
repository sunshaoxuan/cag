from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_creates_phase1_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.sqlite"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    inspector = inspect(create_engine(database_url))
    tables = set(inspector.get_table_names())
    assert {
        "alembic_version",
        "projects",
        "conversations",
        "tasks",
        "task_events",
    } <= tables
    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
    assert {"workspace_id", "workspace_path", "workspace_commit"} <= task_columns
    assert {"harness_profile", "learning_mode"} <= task_columns
    assert {
        "harness_runs",
        "agent_runs",
        "agent_artifacts",
        "approval_requests",
        "quality_scores",
    } <= tables
    source_columns = {
        column["name"]
        for column in inspector.get_columns("knowledge_sources")
    }
    assert {
        "source_type",
        "source_key",
        "reference",
        "credential_ref",
        "last_collected_at",
    } <= source_columns
    assert "duplicate_files" in {
        column["name"]
        for column in inspector.get_columns("knowledge_ingestions")
    }

    command.downgrade(config, "20260727_0008")
    downgraded = inspect(create_engine(database_url))
    assert "source_key" not in {
        column["name"]
        for column in downgraded.get_columns("knowledge_sources")
    }
    assert "duplicate_files" not in {
        column["name"]
        for column in downgraded.get_columns("knowledge_ingestions")
    }

    command.upgrade(config, "head")
