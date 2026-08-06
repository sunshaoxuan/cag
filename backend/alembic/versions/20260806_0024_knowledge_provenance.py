"""Close file, entry, document and chunk provenance links.

Revision ID: 20260806_0024
Revises: 20260806_0023
Create Date: 2026-08-06
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import PurePosixPath
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "20260806_0024"
down_revision: str | Sequence[str] | None = "20260806_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    entry_columns = {
        item["name"]
        for item in inspector.get_columns("knowledge_source_entries")
    }
    entry_indexes = {
        item["name"]
        for item in inspector.get_indexes("knowledge_source_entries")
    }
    document_columns = {
        item["name"]: item
        for item in inspector.get_columns("knowledge_documents")
    }
    if "raw_content_hash" not in entry_columns:
        op.add_column(
            "knowledge_source_entries",
            sa.Column(
                "raw_content_hash", sa.String(length=64), nullable=True
            ),
        )
    if "ix_knowledge_source_entries_raw_content_hash" not in entry_indexes:
        op.create_index(
            "ix_knowledge_source_entries_raw_content_hash",
            "knowledge_source_entries",
            ["raw_content_hash"],
            unique=False,
        )
    if "source_entry_id" not in document_columns:
        op.add_column(
            "knowledge_documents",
            sa.Column(
                "source_entry_id", sa.String(length=36), nullable=True
            ),
        )
    missing_entries = bind.execute(
        sa.text(
            "SELECT d.source_id, d.canonical_path, d.content_hash, "
            "d.processing_mode, d.processor_fingerprint, d.created_at "
            "FROM knowledge_documents d "
            "LEFT JOIN knowledge_source_entries e "
            "ON e.source_id = d.source_id "
            "AND e.relative_path = d.canonical_path "
            "WHERE e.id IS NULL"
        )
    ).mappings()
    now = datetime.now(timezone.utc)
    for item in missing_entries:
        bind.execute(
            sa.text(
                "INSERT INTO knowledge_source_entries ("
                "source_id, relative_path, entry_kind, extension, "
                "processing_mode, processing_status, reason_code, present, "
                "processor_fingerprint, content_hash, first_seen_at, "
                "last_seen_at, processed_at, id"
                ") VALUES ("
                ":source_id, :relative_path, 'file', :extension, "
                ":processing_mode, 'indexed', 'document_provenance_backfill', "
                "true, :processor_fingerprint, :content_hash, :first_seen_at, "
                ":last_seen_at, :processed_at, :id"
                ")"
            ),
            {
                "source_id": item["source_id"],
                "relative_path": item["canonical_path"],
                "extension": PurePosixPath(
                    item["canonical_path"]
                ).suffix.lower(),
                "processing_mode": item["processing_mode"],
                "processor_fingerprint": item["processor_fingerprint"],
                "content_hash": item["content_hash"],
                "first_seen_at": item["created_at"] or now,
                "last_seen_at": now,
                "processed_at": now,
                "id": str(uuid.uuid4()),
            },
        )
    bind.execute(
        sa.text(
            "UPDATE knowledge_documents SET source_entry_id = ("
            "SELECT e.id FROM knowledge_source_entries e "
            "WHERE e.source_id = knowledge_documents.source_id "
            "AND e.relative_path = knowledge_documents.canonical_path"
            ") WHERE source_entry_id IS NULL"
        )
    )
    missing_links = bind.scalar(
        sa.text(
            "SELECT count(*) FROM knowledge_documents "
            "WHERE source_entry_id IS NULL"
        )
    )
    if missing_links:
        raise RuntimeError("Knowledge document provenance backfill failed")

    inspector = sa.inspect(bind)
    document_columns = {
        item["name"]: item
        for item in inspector.get_columns("knowledge_documents")
    }
    unique_columns = {
        tuple(item.get("column_names") or ())
        for item in inspector.get_unique_constraints("knowledge_documents")
    }
    foreign_key_columns = {
        tuple(item.get("constrained_columns") or ())
        for item in inspector.get_foreign_keys("knowledge_documents")
    }
    document_indexes = {
        item["name"]
        for item in inspector.get_indexes("knowledge_documents")
    }
    needs_batch = (
        document_columns["source_entry_id"]["nullable"]
        or ("source_entry_id",) not in unique_columns
        or ("source_entry_id",) not in foreign_key_columns
        or "ix_knowledge_documents_source_entry_id" not in document_indexes
    )
    if needs_batch:
        with op.batch_alter_table("knowledge_documents") as batch:
            if document_columns["source_entry_id"]["nullable"]:
                batch.alter_column(
                    "source_entry_id",
                    existing_type=sa.String(length=36),
                    nullable=False,
                )
            if ("source_entry_id",) not in unique_columns:
                batch.create_unique_constraint(
                    "uq_knowledge_documents_source_entry_id",
                    ["source_entry_id"],
                )
            if ("source_entry_id",) not in foreign_key_columns:
                batch.create_foreign_key(
                    "fk_knowledge_documents_source_entry_id",
                    "knowledge_source_entries",
                    ["source_entry_id"],
                    ["id"],
                    ondelete="CASCADE",
                )
            if (
                "ix_knowledge_documents_source_entry_id"
                not in document_indexes
            ):
                batch.create_index(
                    "ix_knowledge_documents_source_entry_id",
                    ["source_entry_id"],
                    unique=True,
                )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    document_indexes = {
        item["name"]
        for item in inspector.get_indexes("knowledge_documents")
    }
    if "ix_knowledge_documents_source_entry_id" in document_indexes:
        op.drop_index(
            "ix_knowledge_documents_source_entry_id",
            table_name="knowledge_documents",
        )
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.drop_column("source_entry_id")
    inspector = sa.inspect(op.get_bind())
    entry_indexes = {
        item["name"]
        for item in inspector.get_indexes("knowledge_source_entries")
    }
    if "ix_knowledge_source_entries_raw_content_hash" in entry_indexes:
        op.drop_index(
            "ix_knowledge_source_entries_raw_content_hash",
            table_name="knowledge_source_entries",
        )
    entry_columns = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns(
            "knowledge_source_entries"
        )
    }
    if "raw_content_hash" in entry_columns:
        op.drop_column("knowledge_source_entries", "raw_content_hash")
