"""Add indexed text paths for bounded knowledge retrieval.

Revision ID: 20260806_0021
Revises: 20260805_0020
Create Date: 2026-08-06
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260806_0021"
down_revision: str | Sequence[str] | None = "20260805_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_search_text_trgm "
        "ON knowledge_chunks USING gin (lower(search_text) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_documents_path_trgm "
        "ON knowledge_documents USING gin (lower(canonical_path) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_code_symbols_name_trgm "
        "ON code_symbols USING gin (lower(name) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_code_symbols_qualified_name_trgm "
        "ON code_symbols USING gin (lower(qualified_name) gin_trgm_ops)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_code_symbols_qualified_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_code_symbols_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_documents_path_trgm")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_search_text_trgm")
