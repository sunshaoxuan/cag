"""Add Phase 2 project configuration and workspace fields.

Revision ID: 20260727_0002
Revises: 20260727_0001
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260727_0002"
down_revision: str | Sequence[str] | None = "20260727_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("repository_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("default_branch", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("config_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("workspace_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("workspace_path", sa.Text(), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("workspace_commit", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "workspace_commit")
    op.drop_column("tasks", "workspace_path")
    op.drop_column("tasks", "workspace_id")
    op.drop_column("projects", "config_version")
    op.drop_column("projects", "default_branch")
    op.drop_column("projects", "repository_url")
