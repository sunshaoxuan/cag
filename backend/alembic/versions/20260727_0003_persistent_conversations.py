"""Add persistent Codex thread identity to conversations.

Revision ID: 20260727_0003
Revises: 20260727_0002
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260727_0003"
down_revision: str | Sequence[str] | None = "20260727_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("codex_thread_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_conversations_codex_thread_id"),
        "conversations",
        ["codex_thread_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_conversations_codex_thread_id"),
        table_name="conversations",
    )
    op.drop_column("conversations", "codex_thread_id")
