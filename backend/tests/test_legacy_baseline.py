from pathlib import Path

from sqlalchemy import create_engine, text

from app.migrations.legacy_baseline import ensure_legacy_baseline


def sqlite_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.as_posix()}"


def test_legacy_conversation_schema_is_safely_stamped(tmp_path: Path) -> None:
    url = sqlite_url(tmp_path / "legacy.sqlite")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id VARCHAR PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE conversations ("
                "id VARCHAR PRIMARY KEY, codex_thread_id VARCHAR, "
                "next_event_sequence INTEGER)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE tasks ("
                "id VARCHAR PRIMARY KEY, workspace_id VARCHAR)"
            )
        )
        connection.execute(text("CREATE TABLE task_events (id VARCHAR PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
    engine.dispose()

    assert ensure_legacy_baseline(url) == "20260727_0004"
    assert ensure_legacy_baseline(url) == "20260727_0004"


def test_empty_database_is_not_stamped_and_partial_schema_fails(
    tmp_path: Path,
) -> None:
    empty_url = sqlite_url(tmp_path / "empty.sqlite")
    assert ensure_legacy_baseline(empty_url) is None

    partial_url = sqlite_url(tmp_path / "partial.sqlite")
    engine = create_engine(partial_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id VARCHAR PRIMARY KEY)"))
    engine.dispose()

    try:
        ensure_legacy_baseline(partial_url)
    except RuntimeError as exc:
        assert "partial core schema" in str(exc)
    else:
        raise AssertionError("Partial legacy schema must fail closed")
