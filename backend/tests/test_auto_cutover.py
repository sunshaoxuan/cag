from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.migrations import auto_cutover


class FakeResult:
    def __init__(self, row=None) -> None:
        self._row = row

    def first(self):
        return self._row


class FakeConnection:
    def __init__(self, row=None) -> None:
        self.row = row
        self.inserts = []

    def execute(self, statement):
        if getattr(statement, "is_select", False):
            return FakeResult(self.row)
        self.inserts.append(statement)
        return FakeResult()


class FakeEngine:
    def __init__(self, row=None) -> None:
        self.connection = FakeConnection(row)
        self.disposed = False

    def connect(self):
        return nullcontext(self.connection)

    def begin(self):
        return nullcontext(self.connection)

    def dispose(self) -> None:
        self.disposed = True


def settings_for(tmp_path: Path, **overrides) -> Settings:
    values = {
        "environment": "test",
        "database_url": (
            "postgresql+psycopg://agent_gateway:test@localhost/cutover"
        ),
        "legacy_sqlite_path": tmp_path / "legacy.sqlite",
        "migration_receipt_root": tmp_path / "receipts",
        "projects_dir": tmp_path / "projects",
        "workspace_root": tmp_path / "workspaces",
    }
    values.update(overrides)
    return Settings(**values)


def test_auto_cutover_skips_disabled_non_postgres_and_absent_source(
    tmp_path: Path,
) -> None:
    assert run_status(
        settings_for(tmp_path, auto_migrate_legacy_sqlite=False)
    ) == "disabled"
    assert run_status(
        settings_for(
            tmp_path,
            database_url=f"sqlite+pysqlite:///{tmp_path / 'target.sqlite'}",
        )
    ) == "skipped"
    result = auto_cutover.run_auto_cutover(settings_for(tmp_path))
    assert result == {"status": "skipped", "reason": "legacy_source_absent"}


def run_status(settings: Settings) -> str:
    return str(auto_cutover.run_auto_cutover(settings)["status"])


def test_auto_cutover_applies_and_records_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "legacy.sqlite"
    source.write_bytes(b"legacy")
    engine = FakeEngine()
    monkeypatch.setattr(auto_cutover, "create_engine", lambda *_, **__: engine)
    monkeypatch.setattr(auto_cutover, "sha256_file", lambda _: "a" * 64)
    monkeypatch.setattr(
        auto_cutover,
        "inspect_sqlite_source",
        lambda _: {"table_counts": {"tasks": 4}, "vector_count": 9},
    )
    monkeypatch.setattr(
        auto_cutover,
        "migrate",
        lambda **_: {
            "target": {"vector_count": 9},
            "tables": [{"table": "tasks"}],
        },
    )

    result = auto_cutover.run_auto_cutover(settings_for(tmp_path))

    assert result["status"] == "completed"
    assert result["verification"]["source_table_counts"] == {"tasks": 4}
    assert result["verification"]["target_vector_count"] == 9
    assert len(engine.connection.inserts) == 1
    assert engine.disposed is True


def test_auto_cutover_is_idempotent_for_matching_database_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "legacy.sqlite"
    source.write_bytes(b"legacy")
    row = SimpleNamespace(
        source_sha256="b" * 64,
        report_path="D:/receipts/cutover",
    )
    engine = FakeEngine(row)
    monkeypatch.setattr(auto_cutover, "create_engine", lambda *_, **__: engine)
    monkeypatch.setattr(auto_cutover, "sha256_file", lambda _: "b" * 64)

    result = auto_cutover.run_auto_cutover(settings_for(tmp_path))

    assert result["status"] == "already_completed"
    assert result["report_path"] == "D:/receipts/cutover"
    assert engine.connection.inserts == []
    assert engine.disposed is True
