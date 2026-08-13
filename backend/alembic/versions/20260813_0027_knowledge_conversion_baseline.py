"""Add knowledge conversion baseline and manifest records."""

from alembic import op
import sqlalchemy as sa


revision = "20260813_0027"
down_revision = "20260810_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_baseline_runs",
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("active_ingestion_id", sa.String(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_counts", sa.JSON(), nullable=False),
        sa.Column("action_counts", sa.JSON(), nullable=False),
        sa.Column("format_counts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["active_ingestion_id"],
            ["knowledge_ingestions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_baseline_runs_source_id",
        "knowledge_baseline_runs",
        ["source_id"],
    )
    op.create_index(
        "ix_knowledge_baseline_runs_active_ingestion_id",
        "knowledge_baseline_runs",
        ["active_ingestion_id"],
    )
    op.create_index(
        "ix_knowledge_baseline_runs_status",
        "knowledge_baseline_runs",
        ["status"],
    )
    op.create_index(
        "ix_knowledge_baseline_runs_manifest_sha256",
        "knowledge_baseline_runs",
        ["manifest_sha256"],
    )
    op.create_index(
        "ix_knowledge_baseline_runs_created_at",
        "knowledge_baseline_runs",
        ["created_at"],
    )
    op.create_table(
        "knowledge_conversion_manifest_items",
        sa.Column("baseline_run_id", sa.String(), nullable=False),
        sa.Column("source_entry_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("extension", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.Column("conversion_action", sa.String(length=32), nullable=False),
        sa.Column("decision_reason", sa.String(length=64), nullable=False),
        sa.Column("capability", sa.String(length=32), nullable=False),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["baseline_run_id"],
            ["knowledge_baseline_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_entry_id"],
            ["knowledge_source_entries.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "baseline_run_id",
            "source_entry_id",
            name="uq_conversion_manifest_run_entry",
        ),
    )
    for column in (
        "baseline_run_id",
        "source_entry_id",
        "document_id",
        "extension",
        "lifecycle_status",
        "conversion_action",
        "decision_reason",
        "capability",
    ):
        op.create_index(
            f"ix_conversion_manifest_{column}",
            "knowledge_conversion_manifest_items",
            [column],
        )


def downgrade() -> None:
    op.drop_table("knowledge_conversion_manifest_items")
    op.drop_table("knowledge_baseline_runs")
