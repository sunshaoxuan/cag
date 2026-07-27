"""add self learning capability governance

Revision ID: 20260727_0007
Revises: 20260727_0006a
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0007"
down_revision = "20260727_0006a"
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", sa.String(length=36), primary_key=True)


def upgrade() -> None:
    op.create_table(
        "capability_assets",
        _id(),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("shadow_runs", sa.Integer(), nullable=False),
        sa.Column("canary_runs", sa.Integer(), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("rolling_quality_delta", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "capability_evaluations",
        _id(),
        sa.Column(
            "asset_id",
            sa.String(36),
            sa.ForeignKey("capability_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("replay_count", sa.Integer(), nullable=False),
        sa.Column("project_coverage", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "capability_promotions",
        _id(),
        sa.Column(
            "asset_id",
            sa.String(36),
            sa.ForeignKey("capability_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(32), nullable=False),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("receipt_path", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "capability_rollbacks",
        _id(),
        sa.Column(
            "asset_id",
            sa.String(36),
            sa.ForeignKey("capability_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("previous_status", sa.String(32), nullable=False),
        sa.Column("restored_status", sa.String(32), nullable=False),
        sa.Column("receipt_path", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "gardener_runs",
        _id(),
        sa.Column("gardener", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "standard_controls",
        _id(),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("framework", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("implementation_status", sa.String(32), nullable=False),
        sa.Column("control_mapping", sa.JSON(), nullable=False),
        sa.Column("evidence_paths", sa.JSON(), nullable=False),
        sa.Column("certification_claimed", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for table in (
        "capability_assets",
        "capability_evaluations",
        "capability_promotions",
        "capability_rollbacks",
        "gardener_runs",
        "standard_controls",
    ):
        op.create_index(f"ix_{table}_id", table, ["id"])
    op.create_index("ix_capability_assets_kind", "capability_assets", ["kind"])
    op.create_index("ix_capability_assets_code", "capability_assets", ["code"])
    op.create_index("ix_capability_assets_status", "capability_assets", ["status"])
    op.create_index(
        "ix_capability_evaluations_asset_id",
        "capability_evaluations",
        ["asset_id"],
    )
    op.create_index(
        "ix_capability_promotions_asset_id",
        "capability_promotions",
        ["asset_id"],
    )
    op.create_index(
        "ix_capability_rollbacks_asset_id",
        "capability_rollbacks",
        ["asset_id"],
    )


def downgrade() -> None:
    for table in (
        "standard_controls",
        "gardener_runs",
        "capability_rollbacks",
        "capability_promotions",
        "capability_evaluations",
        "capability_assets",
    ):
        op.drop_table(table)
