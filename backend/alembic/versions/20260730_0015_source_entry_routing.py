"""Add durable source entries and processing fingerprints.

Revision ID: 20260730_0015
Revises: 20260729_0014
Create Date: 2026-07-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_0015"
down_revision: str | Sequence[str] | None = "20260729_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    with op.batch_alter_table("knowledge_ingestion_rejections") as batch:
        batch.alter_column(
            "file_size",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=True,
        )
    document_columns = {
        item["name"]
        for item in inspector.get_columns("knowledge_documents")
    }
    document_indexes = {
        item["name"]
        for item in inspector.get_indexes("knowledge_documents")
    }
    if (
        "processing_mode" not in document_columns
        or "processor_fingerprint" not in document_columns
    ):
        with op.batch_alter_table("knowledge_documents") as batch:
            if "processing_mode" not in document_columns:
                batch.add_column(
                    sa.Column(
                        "processing_mode",
                        sa.String(length=32),
                        nullable=False,
                        server_default="legacy",
                    )
                )
            if "processor_fingerprint" not in document_columns:
                batch.add_column(
                    sa.Column(
                        "processor_fingerprint",
                        sa.String(length=64),
                        nullable=True,
                    )
                )
    if "ix_knowledge_documents_processing_mode" not in document_indexes:
        op.create_index(
            "ix_knowledge_documents_processing_mode",
            "knowledge_documents",
            ["processing_mode"],
        )
    if (
        "ix_knowledge_documents_processor_fingerprint"
        not in document_indexes
    ):
        op.create_index(
            "ix_knowledge_documents_processor_fingerprint",
            "knowledge_documents",
            ["processor_fingerprint"],
        )
    op.create_table(
        "knowledge_source_entries",
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column(
            "entry_kind",
            sa.String(length=32),
            nullable=False,
            server_default="file",
        ),
        sa.Column(
            "extension",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "processing_mode",
            sa.String(length=32),
            nullable=False,
            server_default="metadata_only",
        ),
        sa.Column(
            "processing_status",
            sa.String(length=32),
            nullable=False,
            server_default="observed",
        ),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column(
            "present",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("last_seen_ingestion_id", sa.String(), nullable=True),
        sa.Column(
            "processor_fingerprint",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["last_seen_ingestion_id"],
            ["knowledge_ingestions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["knowledge_sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "relative_path",
            name="uq_knowledge_source_entries_source_path",
        ),
    )
    for column in (
        "content_hash",
        "entry_kind",
        "extension",
        "last_seen_at",
        "last_seen_ingestion_id",
        "present",
        "processing_mode",
        "processing_status",
        "processor_fingerprint",
        "reason_code",
        "source_id",
    ):
        op.create_index(
            f"ix_knowledge_source_entries_{column}",
            "knowledge_source_entries",
            [column],
        )


def downgrade() -> None:
    op.drop_table("knowledge_source_entries")
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.drop_index(
            "ix_knowledge_documents_processor_fingerprint"
        )
        batch.drop_index("ix_knowledge_documents_processing_mode")
        batch.drop_column("processor_fingerprint")
        batch.drop_column("processing_mode")
    with op.batch_alter_table("knowledge_ingestion_rejections") as batch:
        batch.alter_column(
            "file_size",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=True,
        )
