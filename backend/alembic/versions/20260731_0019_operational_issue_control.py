"""Correct validation status and operational issue controls.

Revision ID: 20260731_0019
Revises: 20260731_0018
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260731_0019"
down_revision: str | Sequence[str] | None = "20260731_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE operational_issues
            SET status = 'validation_completed',
                approval_status = 'not_requested',
                resolution = COALESCE(
                    resolution,
                    'Controlled deployment validation completed'
                )
            WHERE source_type = 'deployment-validation'
              AND status = 'rejected'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE operational_issues
            SET status = 'rejected',
                approval_status = 'rejected'
            WHERE source_type = 'deployment-validation'
              AND status = 'validation_completed'
            """
        )
    )
