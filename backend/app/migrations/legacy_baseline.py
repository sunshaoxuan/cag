from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.config import get_settings


CORE_TABLES = {"projects", "conversations", "tasks", "task_events"}


def ensure_legacy_baseline(database_url: str) -> str | None:
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if not CORE_TABLES.intersection(tables):
            return None
        if not CORE_TABLES.issubset(tables):
            raise RuntimeError(
                "Legacy database has a partial core schema and cannot be baselined"
            )

        with engine.begin() as connection:
            if "alembic_version" in tables:
                current = connection.scalar(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                if current:
                    return str(current)
            else:
                connection.execute(
                    text(
                        "CREATE TABLE alembic_version "
                        "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                    )
                )

            columns = {
                table: {item["name"] for item in inspector.get_columns(table)}
                for table in CORE_TABLES
            }
            if "capability_assets" in tables:
                revision = "20260727_0007"
            elif "harness_runs" in tables:
                source_columns = (
                    {item["name"] for item in inspector.get_columns("knowledge_sources")}
                    if "knowledge_sources" in tables
                    else set()
                )
                revision = (
                    "20260727_0006a"
                    if "index_fingerprint" in source_columns
                    else "20260727_0006"
                )
            elif "knowledge_sources" in tables:
                revision = "20260727_0005"
            elif "next_event_sequence" in columns["conversations"]:
                revision = "20260727_0004"
            elif "codex_thread_id" in columns["conversations"]:
                revision = "20260727_0003"
            elif "workspace_id" in columns["tasks"]:
                revision = "20260727_0002"
            else:
                revision = "20260727_0001"
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": revision},
            )
            return revision
    finally:
        engine.dispose()


def main() -> None:
    revision = ensure_legacy_baseline(get_settings().database_url)
    if revision:
        print(f"Database baseline: {revision}")


if __name__ == "__main__":
    main()
