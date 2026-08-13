"""Add content-addressed artifact evidence foundation."""

from alembic import op
import sqlalchemy as sa


revision = "20260813_0029"
down_revision = "20260813_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_artifacts",
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(length=255), nullable=False),
        sa.Column("artifact_kind", sa.String(length=32), nullable=False),
        sa.Column("retention_policy", sa.String(length=32), nullable=False),
        sa.Column("encryption", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("sha256", "artifact_kind", "retention_policy", "status", "created_at"):
        op.create_index(
            f"ix_knowledge_artifacts_{column}", "knowledge_artifacts", [column],
            unique=column == "sha256",
        )
    op.create_table(
        "knowledge_artifact_locations",
        sa.Column("artifact_id", sa.String(), nullable=False),
        sa.Column("source_entry_id", sa.String(), nullable=True),
        sa.Column("location_type", sa.String(length=32), nullable=False),
        sa.Column("relative_path_snapshot", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["knowledge_artifacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entry_id"], ["knowledge_source_entries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artifact_id", "source_entry_id", "location_type", name="uq_artifact_location_evidence"),
    )
    for column in ("artifact_id", "source_entry_id", "location_type"):
        op.create_index(f"ix_knowledge_artifact_locations_{column}", "knowledge_artifact_locations", [column])
    op.create_table(
        "knowledge_object_replicas",
        sa.Column("artifact_id", sa.String(), nullable=False),
        sa.Column("replica_name", sa.String(length=64), nullable=False),
        sa.Column("backend", sa.String(length=32), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("version_id", sa.String(length=255), nullable=True),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["knowledge_artifacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artifact_id", "replica_name", name="uq_object_replica_artifact_name"),
    )
    for column in ("artifact_id", "replica_name", "backend", "checksum_sha256", "status"):
        op.create_index(f"ix_knowledge_object_replicas_{column}", "knowledge_object_replicas", [column])
    op.create_table(
        "knowledge_artifact_transformations",
        sa.Column("input_artifact_id", sa.String(), nullable=False),
        sa.Column("output_artifact_id", sa.String(), nullable=False),
        sa.Column("transformation_type", sa.String(length=64), nullable=False),
        sa.Column("processor", sa.String(length=128), nullable=False),
        sa.Column("processor_version", sa.String(length=64), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["input_artifact_id"], ["knowledge_artifacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["output_artifact_id"], ["knowledge_artifacts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("input_artifact_id", "output_artifact_id", "transformation_type"):
        op.create_index(f"ix_knowledge_artifact_transformations_{column}", "knowledge_artifact_transformations", [column])
    op.create_index("ix_knowledge_artifact_transformations_fingerprint", "knowledge_artifact_transformations", ["fingerprint"], unique=True)
    op.create_table(
        "knowledge_artifact_reconciliation_runs",
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("checked_artifacts", sa.Integer(), nullable=False),
        sa.Column("checked_replicas", sa.Integer(), nullable=False),
        sa.Column("repaired_replicas", sa.Integer(), nullable=False),
        sa.Column("missing_replicas", sa.Integer(), nullable=False),
        sa.Column("corrupt_replicas", sa.Integer(), nullable=False),
        sa.Column("orphan_objects", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_artifact_reconciliation_runs_status", "knowledge_artifact_reconciliation_runs", ["status"])
    op.create_index("ix_knowledge_artifact_reconciliation_runs_created_at", "knowledge_artifact_reconciliation_runs", ["created_at"])


def downgrade() -> None:
    op.drop_table("knowledge_artifact_reconciliation_runs")
    op.drop_table("knowledge_artifact_transformations")
    op.drop_table("knowledge_object_replicas")
    op.drop_table("knowledge_artifact_locations")
    op.drop_table("knowledge_artifacts")
