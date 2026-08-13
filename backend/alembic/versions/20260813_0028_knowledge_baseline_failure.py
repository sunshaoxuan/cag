"""Add terminal failure evidence to knowledge baselines."""

from alembic import op
import sqlalchemy as sa


revision = "20260813_0028"
down_revision = "20260813_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_baseline_runs",
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_baseline_runs", "error")
