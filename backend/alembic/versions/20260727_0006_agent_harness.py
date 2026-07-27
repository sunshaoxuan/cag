"""add governed agent harness

Revision ID: 20260727_0006
Revises: 20260727_0005
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0006"
down_revision = "20260727_0005"
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", sa.String(length=36), primary_key=True)


def upgrade() -> None:
    op.add_column("tasks", sa.Column("harness_profile", sa.String(32), nullable=True))
    op.add_column("tasks", sa.Column("learning_mode", sa.String(32), nullable=True))
    op.execute("UPDATE tasks SET harness_profile='single', learning_mode='capture'")
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("harness_profile", nullable=False)
        batch.alter_column("learning_mode", nullable=False)

    op.create_table(
        "harness_profiles", _id(),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "harness_runs", _id(),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("profile", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("max_parallel", sa.Integer(), nullable=False),
        sa.Column("task_contract", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "agent_runs", _id(),
        sa.Column("harness_run_id", sa.String(36), sa.ForeignKey("harness_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_key", sa.String(128), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("phase", sa.String(32), nullable=False),
        sa.Column("access_mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("budget_seconds", sa.Integer(), nullable=False),
        sa.Column("runtime_thread_id", sa.String(128)),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "task_graph_nodes", _id(),
        sa.Column("harness_run_id", sa.String(36), sa.ForeignKey("harness_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_key", sa.String(128), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
    )
    op.create_table(
        "agent_artifacts", _id(),
        sa.Column("agent_run_id", sa.String(36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "review_findings", _id(),
        sa.Column("agent_run_id", sa.String(36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "verification_runs", _id(),
        sa.Column("harness_run_id", sa.String(36), sa.ForeignKey("harness_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("validator", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "quality_scores", _id(),
        sa.Column("harness_run_id", sa.String(36), sa.ForeignKey("harness_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overall", sa.Float(), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "learning_signals", _id(),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("signal_type", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "approval_requests", _id(),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_run_id", sa.String(36), sa.ForeignKey("agent_runs.id", ondelete="SET NULL")),
        sa.Column("request_type", sa.String(64), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("policy_decision", sa.String(32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", sa.String(128)),
        sa.Column("resolution_note", sa.Text()),
    )
    for table in ("harness_profiles", "harness_runs", "agent_runs", "task_graph_nodes", "agent_artifacts", "review_findings", "verification_runs", "quality_scores", "learning_signals", "approval_requests"):
        op.create_index(f"ix_{table}_id", table, ["id"])
    op.create_index("ix_agent_runs_task_id", "agent_runs", ["task_id"])
    op.create_index("ix_approval_requests_task_id", "approval_requests", ["task_id"])


def downgrade() -> None:
    for table in ("approval_requests", "learning_signals", "quality_scores", "verification_runs", "review_findings", "agent_artifacts", "task_graph_nodes", "agent_runs", "harness_runs", "harness_profiles"):
        op.drop_table(table)
    op.drop_column("tasks", "learning_mode")
    op.drop_column("tasks", "harness_profile")
