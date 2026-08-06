"""Add source processor fingerprint for incremental knowledge learning.

Revision ID: 20260806_0022
Revises: 20260806_0021
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260806_0022"
down_revision: str | Sequence[str] | None = "20260806_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {
        item["name"] for item in inspector.get_columns("knowledge_sources")
    }
    indexes = {
        item["name"] for item in inspector.get_indexes("knowledge_sources")
    }
    if "processor_fingerprint" not in columns:
        op.add_column(
            "knowledge_sources",
            sa.Column(
                "processor_fingerprint",
                sa.String(length=64),
                nullable=True,
            ),
        )
    if "ix_knowledge_sources_processor_fingerprint" not in indexes:
        op.create_index(
            "ix_knowledge_sources_processor_fingerprint",
            "knowledge_sources",
            ["processor_fingerprint"],
            unique=False,
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    indexes = {
        item["name"] for item in inspector.get_indexes("knowledge_sources")
    }
    columns = {
        item["name"] for item in inspector.get_columns("knowledge_sources")
    }
    if "ix_knowledge_sources_processor_fingerprint" in indexes:
        op.drop_index(
            "ix_knowledge_sources_processor_fingerprint",
            table_name="knowledge_sources",
        )
    if "processor_fingerprint" in columns:
        op.drop_column("knowledge_sources", "processor_fingerprint")
