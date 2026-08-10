from pathlib import Path

from alembic import command
from alembic.config import Config
from datetime import UTC, datetime

from sqlalchemy import create_engine, inspect, text


def test_alembic_upgrade_and_validation_status_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "operations-control.sqlite"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "20260731_0018")

    now = datetime.now(UTC)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO projects (id, code, name, created_at)
                VALUES (:id, :code, :name, :created_at)
                """
            ),
            {
                "id": "project-validation",
                "code": "validation",
                "name": "Validation",
                "created_at": now,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO operational_issues (
                    id, project_id, code, fingerprint, source_type, source_id,
                    title, summary, severity, status, occurrence_count,
                    evidence, allowed_actions, approval_status,
                    evaluation_status, first_seen_at, last_seen_at,
                    created_at, updated_at
                ) VALUES (
                    :id, :project_id, :code, :fingerprint, :source_type,
                    :source_id, :title, :summary, :severity, :status,
                    :occurrence_count, :evidence, :allowed_actions,
                    :approval_status, :evaluation_status, :first_seen_at,
                    :last_seen_at, :created_at, :updated_at
                )
                """
            ),
            {
                "id": "issue-validation",
                "project_id": "project-validation",
                "code": "OI-VALIDATION",
                "fingerprint": "f" * 64,
                "source_type": "deployment-validation",
                "source_id": "0.21.0",
                "title": "Controlled deployment validation",
                "summary": "Validation completed",
                "severity": "low",
                "status": "rejected",
                "occurrence_count": 1,
                "evidence": "{}",
                "allowed_actions": "[]",
                "approval_status": "rejected",
                "evaluation_status": "not_started",
                "first_seen_at": now,
                "last_seen_at": now,
                "created_at": now,
                "updated_at": now,
            },
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        migrated = connection.execute(
            text(
                """
                SELECT status, approval_status
                FROM operational_issues
                WHERE id = 'issue-validation'
                """
            )
        ).one()
    assert migrated.status == "validation_completed"
    assert migrated.approval_status == "not_requested"

    head_inspector = inspect(create_engine(database_url))
    source_entry_columns = {
        column["name"]
        for column in head_inspector.get_columns("knowledge_source_entries")
    }
    assert {"extractor", "extractor_version"} <= source_entry_columns
    conversation_columns = {
        column["name"]
        for column in head_inspector.get_columns("conversations")
    }
    assert {"client_id", "idempotency_key", "request_hash"} <= (
        conversation_columns
    )
    command.downgrade(config, "20260731_0019")
    xlsx_evidence_downgraded = inspect(create_engine(database_url))
    assert "extractor" not in {
        column["name"]
        for column in xlsx_evidence_downgraded.get_columns(
            "knowledge_source_entries"
        )
    }
    command.upgrade(config, "head")

    command.downgrade(config, "20260731_0018")
    with engine.connect() as connection:
        downgraded = connection.execute(
            text(
                """
                SELECT status, approval_status
                FROM operational_issues
                WHERE id = 'issue-validation'
                """
            )
        ).one()
    assert downgraded.status == "rejected"
    assert downgraded.approval_status == "rejected"
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
        "sync_mode",
        "sync_interval_minutes",
        "next_sync_at",
        "last_sync_attempt_at",
        "last_content_change_at",
        "consecutive_failures",
    } <= source_columns
    ingestion_columns = {
        column["name"]
        for column in inspector.get_columns("knowledge_ingestions")
    }
    assert {
        "duplicate_files",
        "changed_files",
        "removed_files",
        "trigger",
        "started_at",
        "skipped_files",
        "rejection_archive_name",
        "rejection_archive_sha256",
        "rejection_archive_created_at",
    } <= ingestion_columns
    assert {
        "code_symbols",
        "code_relations",
        "code_document_links",
        "knowledge_ingestion_rejections",
        "knowledge_source_entries",
        "queue_items",
        "queue_workers",
        "data_migration_receipts",
    } <= tables
    document_columns = {
        column["name"]
        for column in inspector.get_columns("knowledge_documents")
    }
    assert {
        "processing_mode",
        "processor_fingerprint",
        "generation_ingestion_id",
    } <= document_columns
    rejection_file_size = next(
        column
        for column in inspector.get_columns(
            "knowledge_ingestion_rejections"
        )
        if column["name"] == "file_size"
    )
    assert str(rejection_file_size["type"]).upper() == "BIGINT"
    operational_issue_columns = {
        column["name"]
        for column in inspector.get_columns("operational_issues")
    }
    assert {
        "resolution_mode",
        "resolution_mode_confidence",
        "resolution_mode_reason",
        "decision_brief",
        "review_recommendation",
        "blocking_finding_count",
        "event_sequence",
    } <= operational_issue_columns

    command.downgrade(config, "20260730_0015")
    generation_downgraded = inspect(create_engine(database_url))
    assert "generation_ingestion_id" not in {
        column["name"]
        for column in generation_downgraded.get_columns(
            "knowledge_documents"
        )
    }
    command.upgrade(config, "head")

    command.downgrade(config, "20260728_0011")
    audit_downgraded = inspect(create_engine(database_url))
    assert "knowledge_ingestion_rejections" not in set(
        audit_downgraded.get_table_names()
    )
    assert "skipped_files" not in {
        column["name"]
        for column in audit_downgraded.get_columns(
            "knowledge_ingestions"
        )
    }
    command.upgrade(config, "head")
    command.downgrade(config, "20260728_0010")
    code_downgraded = inspect(create_engine(database_url))
    assert "code_symbols" not in set(code_downgraded.get_table_names())
    command.upgrade(config, "head")
    command.downgrade(config, "20260728_0009")
    scheduler_downgraded = inspect(create_engine(database_url))
    assert "sync_mode" not in {
        column["name"]
        for column in scheduler_downgraded.get_columns("knowledge_sources")
    }
    assert "trigger" not in {
        column["name"]
        for column in scheduler_downgraded.get_columns(
            "knowledge_ingestions"
        )
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
