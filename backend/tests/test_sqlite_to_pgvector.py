import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, insert, select

from app.migrations.sqlite_to_pgvector import (
    MigrationBlockedError,
    _copy_tables,
    inspect_sqlite_source,
    main,
    migrate,
    redact_database_url,
)
from app.models import Base, KnowledgeIngestion, Tenant


def sqlite_engine(path: Path):
    return create_engine(f"sqlite+pysqlite:///{path.as_posix()}")


def test_inspection_blocks_active_knowledge_ingestion(tmp_path: Path) -> None:
    source_path = tmp_path / "active.sqlite"
    engine = sqlite_engine(source_path)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(KnowledgeIngestion).values(
                id="fbbd9ac2-f5cf-46e6-a70a-0d0c017177fd",
                source_id="4b2dc231-f56d-49d8-b6db-1fb401d0c743",
                status="running",
            )
        )
    engine.dispose()

    inspection = inspect_sqlite_source(source_path)
    assert inspection["integrity"] == "ok"
    assert inspection["active_ingestions"] == [
        {
            "id": "fbbd9ac2-f5cf-46e6-a70a-0d0c017177fd",
            "status": "running",
        }
    ]

    with pytest.raises(MigrationBlockedError, match="active knowledge"):
        migrate(
            source_path=source_path,
            target_url=(
                "postgresql+psycopg://agent_gateway@127.0.0.1/"
                "agent_gateway"
            ),
            output_dir=tmp_path / "evidence",
            apply=False,
        )


def test_copy_preserves_rows_and_physical_ids(tmp_path: Path) -> None:
    source_engine = sqlite_engine(tmp_path / "source.sqlite")
    target_engine = sqlite_engine(tmp_path / "target.sqlite")
    Base.metadata.create_all(source_engine)
    Base.metadata.create_all(target_engine)
    tenant_id = "c02c12af-bb58-4883-ae90-308cf08a6f9d"
    with source_engine.begin() as connection:
        connection.execute(
            insert(Tenant).values(
                id=tenant_id,
                code="customer-a",
                name="Customer A",
            )
        )

    receipts = _copy_tables(
        source_engine,
        target_engine,
        batch_size=10,
    )

    tenant_receipt = next(
        item for item in receipts if item.table == "tenants"
    )
    assert tenant_receipt.source_rows == 1
    assert tenant_receipt.target_rows == 1
    assert tenant_receipt.source_id_sha256 == tenant_receipt.target_id_sha256
    with target_engine.connect() as connection:
        assert connection.scalar(select(Tenant.id)) == tenant_id
    source_engine.dispose()
    target_engine.dispose()


def test_target_url_redacts_password() -> None:
    value = redact_database_url(
        "postgresql+psycopg://agent_gateway:secret@postgres/agent_gateway"
    )

    assert "secret" not in value
    assert "***" in value


def test_cli_reports_active_ingestion_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / "active-cli.sqlite"
    engine = sqlite_engine(source_path)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(KnowledgeIngestion).values(
                id="722625e0-f466-41a6-915a-aa9150c3c955",
                source_id="74777f17-a68a-45ba-87ed-7d2b135d6e0e",
                status="queued",
            )
        )
    engine.dispose()
    output_dir = tmp_path / "receipt"
    monkeypatch.setenv(
        "AGENT_GATEWAY_MIGRATION_TARGET_URL",
        "postgresql+psycopg://agent_gateway:secret@postgres/target",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sqlite_to_pgvector",
            "--source",
            str(source_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert main() == 2
    captured = capsys.readouterr()
    assert "Migration blocked" in captured.err
    assert "Traceback" not in captured.err
    report = (output_dir / "migration_report.json").read_text(
        encoding="utf-8"
    )
    assert '"status": "blocked"' in report
    assert "secret" not in report
