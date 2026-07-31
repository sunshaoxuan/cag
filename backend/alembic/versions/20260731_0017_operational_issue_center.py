"""Add the governed operational issue center.

Revision ID: 20260731_0017
Revises: 20260730_0016
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260731_0017"
down_revision: str | Sequence[str] | None = "20260730_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operational_issues",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("parent_issue_id", sa.String(), nullable=True),
        sa.Column("implementation_task_id", sa.String(), nullable=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("boundary", sa.String(length=64), nullable=True),
        sa.Column("boundary_confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("allowed_actions", sa.JSON(), nullable=False),
        sa.Column("required_human_input", sa.Text(), nullable=True),
        sa.Column("approval_status", sa.String(length=32), nullable=False),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("improvement_branch", sa.String(length=255), nullable=True),
        sa.Column("evaluation_status", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("closed_by", sa.String(length=128), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["implementation_task_id"],
            ["tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_issue_id"],
            ["operational_issues.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "fingerprint",
            name="uq_operational_issues_project_fingerprint",
        ),
        sa.UniqueConstraint("code", name="uq_operational_issues_code"),
    )
    for column in (
        "approval_status",
        "boundary",
        "code",
        "evaluation_status",
        "fingerprint",
        "implementation_task_id",
        "last_seen_at",
        "parent_issue_id",
        "project_id",
        "severity",
        "source_id",
        "source_type",
        "status",
    ):
        op.create_index(
            op.f(f"ix_operational_issues_{column}"),
            "operational_issues",
            [column],
        )

    op.create_table(
        "operational_issue_occurrences",
        sa.Column("issue_id", sa.String(), nullable=False),
        sa.Column("external_event_id", sa.String(length=128), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("error_type", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["operational_issues.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "external_event_id",
            name="uq_operational_issue_occurrences_external_event_id",
        ),
    )
    for column in ("event_type", "issue_id", "occurred_at"):
        op.create_index(
            op.f(f"ix_operational_issue_occurrences_{column}"),
            "operational_issue_occurrences",
            [column],
        )

    op.create_table(
        "operational_issue_artifacts",
        sa.Column("issue_id", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["operational_issues.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "issue_id",
            "artifact_type",
            "revision",
            name="uq_operational_issue_artifacts_revision",
        ),
    )
    op.create_index(
        op.f("ix_operational_issue_artifacts_artifact_type"),
        "operational_issue_artifacts",
        ["artifact_type"],
    )
    op.create_index(
        op.f("ix_operational_issue_artifacts_issue_id"),
        "operational_issue_artifacts",
        ["issue_id"],
    )

    op.create_table(
        "operational_issue_events",
        sa.Column("issue_id", sa.String(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["operational_issues.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "issue_id",
            "sequence",
            name="uq_operational_issue_events_sequence",
        ),
    )
    for column in ("created_at", "issue_id", "type"):
        op.create_index(
            op.f(f"ix_operational_issue_events_{column}"),
            "operational_issue_events",
            [column],
        )

    with op.batch_alter_table("queue_items") as batch_op:
        batch_op.drop_constraint(
            "exactly_one_resource",
            type_="check",
        )
        batch_op.add_column(
            sa.Column("issue_id", sa.String(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_queue_items_issue_id_operational_issues",
            "operational_issues",
            ["issue_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_check_constraint(
            "exactly_one_resource",
            "(CASE WHEN task_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN ingestion_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN issue_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
        )
    op.create_index(
        op.f("ix_queue_items_issue_id"),
        "queue_items",
        ["issue_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_queue_items_issue_id"), table_name="queue_items")
    with op.batch_alter_table("queue_items") as batch_op:
        batch_op.drop_constraint(
            "exactly_one_resource",
            type_="check",
        )
        batch_op.drop_constraint(
            "fk_queue_items_issue_id_operational_issues",
            type_="foreignkey",
        )
        batch_op.drop_column("issue_id")
        batch_op.create_check_constraint(
            "exactly_one_resource",
            "(task_id IS NOT NULL AND ingestion_id IS NULL) OR "
            "(task_id IS NULL AND ingestion_id IS NOT NULL)",
        )
    for column in ("type", "issue_id", "created_at"):
        op.drop_index(
            op.f(f"ix_operational_issue_events_{column}"),
            table_name="operational_issue_events",
        )
    op.drop_table("operational_issue_events")
    op.drop_index(
        op.f("ix_operational_issue_artifacts_issue_id"),
        table_name="operational_issue_artifacts",
    )
    op.drop_index(
        op.f("ix_operational_issue_artifacts_artifact_type"),
        table_name="operational_issue_artifacts",
    )
    op.drop_table("operational_issue_artifacts")
    for column in ("occurred_at", "issue_id", "event_type"):
        op.drop_index(
            op.f(f"ix_operational_issue_occurrences_{column}"),
            table_name="operational_issue_occurrences",
        )
    op.drop_table("operational_issue_occurrences")
    for column in (
        "status",
        "source_type",
        "source_id",
        "severity",
        "project_id",
        "parent_issue_id",
        "last_seen_at",
        "implementation_task_id",
        "fingerprint",
        "evaluation_status",
        "code",
        "boundary",
        "approval_status",
    ):
        op.drop_index(
            op.f(f"ix_operational_issues_{column}"),
            table_name="operational_issues",
        )
    op.drop_table("operational_issues")
