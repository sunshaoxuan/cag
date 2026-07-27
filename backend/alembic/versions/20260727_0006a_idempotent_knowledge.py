"""add idempotent incremental knowledge indexing

Revision ID: 20260727_0006a
Revises: 20260727_0006
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0006a"
down_revision = "20260727_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    source_columns = {
        column["name"] for column in inspector.get_columns("knowledge_sources")
    }
    ingestion_columns = {
        column["name"] for column in inspector.get_columns("knowledge_ingestions")
    }
    if "index_fingerprint" not in source_columns:
        op.add_column(
            "knowledge_sources",
            sa.Column("index_fingerprint", sa.String(64), nullable=True),
        )
    if "unchanged_files" not in ingestion_columns:
        op.add_column(
            "knowledge_ingestions",
            sa.Column("unchanged_files", sa.Integer(), nullable=False, server_default="0"),
        )
    if "vectors_reused" not in ingestion_columns:
        op.add_column(
            "knowledge_ingestions",
            sa.Column("vectors_reused", sa.Integer(), nullable=False, server_default="0"),
        )
    document_constraints = {
        item["name"]
        for item in inspector.get_unique_constraints("knowledge_documents")
    }
    if "uq_knowledge_documents_source_path" not in document_constraints:
        with op.batch_alter_table("knowledge_documents") as batch:
            batch.create_unique_constraint(
                "uq_knowledge_documents_source_path",
                ["source_id", "canonical_path"],
            )
    chunk_constraints = {
        item["name"]
        for item in inspector.get_unique_constraints("knowledge_chunks")
    }
    if "uq_knowledge_chunks_document_ordinal" not in chunk_constraints:
        with op.batch_alter_table("knowledge_chunks") as batch:
            batch.create_unique_constraint(
                "uq_knowledge_chunks_document_ordinal",
                ["document_id", "ordinal"],
            )


def downgrade() -> None:
    with op.batch_alter_table("knowledge_chunks") as batch:
        batch.drop_constraint(
            "uq_knowledge_chunks_document_ordinal", type_="unique"
        )
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.drop_constraint(
            "uq_knowledge_documents_source_path", type_="unique"
        )
    op.drop_column("knowledge_ingestions", "vectors_reused")
    op.drop_column("knowledge_ingestions", "unchanged_files")
    op.drop_column("knowledge_sources", "index_fingerprint")
