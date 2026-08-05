"""Add XLSX processing evidence to source entries.

Revision ID: 20260805_0020
Revises: 20260731_0019
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260805_0020"
down_revision: str | Sequence[str] | None = "20260731_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("knowledge_source_entries") as batch:
        batch.add_column(
            sa.Column("extractor", sa.String(length=64), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "extractor_version",
                sa.String(length=32),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("knowledge_source_entries") as batch:
        batch.drop_column("extractor_version")
        batch.drop_column("extractor")
