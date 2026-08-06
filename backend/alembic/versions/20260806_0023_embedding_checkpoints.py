"""Add durable embedding checkpoints for resumable knowledge ingestion.

Revision ID: 20260806_0023
Revises: 20260806_0022
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = "20260806_0023"
down_revision: str | Sequence[str] | None = "20260806_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_embedding_cache",
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "last_used_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key"),
    )
    op.create_index(
        "ix_knowledge_embedding_cache_cache_key",
        "knowledge_embedding_cache",
        ["cache_key"],
        unique=True,
    )
    op.create_index(
        "ix_knowledge_embedding_cache_embedding_model",
        "knowledge_embedding_cache",
        ["embedding_model"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_embedding_cache_last_used_at",
        "knowledge_embedding_cache",
        ["last_used_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("knowledge_embedding_cache")
