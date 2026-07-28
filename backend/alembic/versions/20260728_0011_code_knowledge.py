"""add governed code knowledge graph

Revision ID: 20260728_0011
Revises: 20260728_0010
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0011"
down_revision = "20260728_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "code_symbols",
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("product_version_id", sa.String(), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("qualified_name", sa.Text(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_version_id"],
            ["product_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "kind",
            "qualified_name",
            "start_line",
            name="uq_code_symbols_document_identity",
        ),
    )
    for name in (
        "document_id",
        "tenant_id",
        "product_version_id",
        "scope",
        "language",
        "kind",
        "name",
        "content_hash",
    ):
        op.create_index(f"ix_code_symbols_{name}", "code_symbols", [name])

    op.create_table(
        "code_relations",
        sa.Column("source_symbol_id", sa.String(), nullable=False),
        sa.Column("target_symbol_id", sa.String(), nullable=True),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("target_name", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_symbol_id"],
            ["code_symbols.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_symbol_id"],
            ["code_symbols.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fingerprint",
            name="uq_code_relations_fingerprint",
        ),
    )
    for name in (
        "source_symbol_id",
        "target_symbol_id",
        "relation_type",
        "fingerprint",
    ):
        op.create_index(f"ix_code_relations_{name}", "code_relations", [name])

    op.create_table(
        "code_document_links",
        sa.Column("symbol_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("link_type", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["code_symbols.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fingerprint",
            name="uq_code_document_links_fingerprint",
        ),
    )
    for name in ("symbol_id", "document_id", "link_type", "fingerprint"):
        op.create_index(
            f"ix_code_document_links_{name}",
            "code_document_links",
            [name],
        )


def downgrade() -> None:
    op.drop_table("code_document_links")
    op.drop_table("code_relations")
    op.drop_table("code_symbols")
