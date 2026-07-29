"""Add the durable PostgreSQL work queue.

Revision ID: 20260729_0014
Revises: 20260729_0013
Create Date: 2026-07-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260729_0014"
down_revision: str | Sequence[str] | None = "20260729_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_migration_receipts",
        sa.Column("migration_key", sa.String(length=128), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("target_revision", sa.String(length=64), nullable=False),
        sa.Column("report_path", sa.Text(), nullable=False),
        sa.Column("verification", sa.JSON(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "migration_key",
            name="uq_data_migration_receipts_migration_key",
        ),
    )
    op.create_index(
        op.f("ix_data_migration_receipts_migration_key"),
        "data_migration_receipts",
        ["migration_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_data_migration_receipts_source_sha256"),
        "data_migration_receipts",
        ["source_sha256"],
        unique=False,
    )
    op.create_table(
        "queue_items",
        sa.Column("queue_name", sa.String(length=64), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("ingestion_id", sa.String(), nullable=True),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=True),
        sa.Column("client_id", sa.String(length=128), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(length=255), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.CheckConstraint(
            "(task_id IS NOT NULL AND ingestion_id IS NULL) OR "
            "(task_id IS NULL AND ingestion_id IS NOT NULL)",
            name=op.f("ck_queue_items_exactly_one_resource"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_queue_items_conversation_id_conversations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["knowledge_ingestions.id"],
            name=op.f("fk_queue_items_ingestion_id_knowledge_ingestions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_queue_items_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name=op.f("fk_queue_items_task_id_tasks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_queue_items")),
        sa.UniqueConstraint("ingestion_id", name="uq_queue_items_ingestion_id"),
        sa.UniqueConstraint("task_id", name="uq_queue_items_task_id"),
    )
    op.create_index(
        "ix_queue_items_claim",
        "queue_items",
        [
            "queue_name",
            "status",
            "available_at",
            "priority",
            "created_at",
        ],
    )
    for column in (
        "available_at",
        "client_id",
        "conversation_id",
        "job_type",
        "lease_expires_at",
        "lease_owner",
        "project_id",
        "queue_name",
        "status",
    ):
        op.create_index(
            op.f(f"ix_queue_items_{column}"),
            "queue_items",
            [column],
        )

    op.create_table(
        "queue_workers",
        sa.Column("worker_key", sa.String(length=255), nullable=False),
        sa.Column("queue_name", sa.String(length=64), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("process_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_item_id", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["current_item_id"],
            ["queue_items.id"],
            name=op.f("fk_queue_workers_current_item_id_queue_items"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_queue_workers")),
        sa.UniqueConstraint("worker_key", name="uq_queue_workers_worker_key"),
    )
    op.create_index(
        op.f("ix_queue_workers_heartbeat_at"),
        "queue_workers",
        ["heartbeat_at"],
    )
    op.create_index(
        op.f("ix_queue_workers_queue_name"),
        "queue_workers",
        ["queue_name"],
    )
    op.create_index(
        op.f("ix_queue_workers_status"),
        "queue_workers",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_queue_workers_status"), table_name="queue_workers")
    op.drop_index(op.f("ix_queue_workers_queue_name"), table_name="queue_workers")
    op.drop_index(
        op.f("ix_queue_workers_heartbeat_at"),
        table_name="queue_workers",
    )
    op.drop_table("queue_workers")
    for column in (
        "status",
        "queue_name",
        "project_id",
        "lease_owner",
        "lease_expires_at",
        "job_type",
        "conversation_id",
        "client_id",
        "available_at",
    ):
        op.drop_index(
            op.f(f"ix_queue_items_{column}"),
            table_name="queue_items",
        )
    op.drop_index("ix_queue_items_claim", table_name="queue_items")
    op.drop_table("queue_items")
    op.drop_index(
        op.f("ix_data_migration_receipts_source_sha256"),
        table_name="data_migration_receipts",
    )
    op.drop_index(
        op.f("ix_data_migration_receipts_migration_key"),
        table_name="data_migration_receipts",
    )
    op.drop_table("data_migration_receipts")
