"""Add enterprise knowledge and Modular RAG records.

Revision ID: 20260727_0005
Revises: 20260727_0004
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models import Base


revision: str = "20260727_0005"
down_revision: str | Sequence[str] | None = "20260727_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLES = [
    "tenants",
    "products",
    "product_versions",
    "knowledge_sources",
    "knowledge_ingestions",
    "knowledge_ingestion_events",
    "knowledge_documents",
    "knowledge_chunks",
    "memory_candidates",
    "knowledge_usages",
    "knowledge_evaluations",
    "risk_records",
    "data_quality_metrics",
    "knowledge_conflicts",
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    for name in TABLES[:3]:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("product_version_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_projects_tenant_id_tenants"),
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            op.f("fk_projects_product_version_id_product_versions"),
            "product_versions",
            ["product_version_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(op.f("ix_projects_tenant_id"), ["tenant_id"])
        batch_op.create_index(
            op.f("ix_projects_product_version_id"), ["product_version_id"]
        )
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "knowledge_mode",
                sa.String(length=32),
                nullable=False,
                server_default="assist",
            )
        )
        batch_op.add_column(sa.Column("knowledge_usage", sa.JSON(), nullable=True))
    for name in TABLES[3:]:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_hnsw "
            "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES[3:]):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("knowledge_usage")
        batch_op.drop_column("knowledge_mode")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index(op.f("ix_projects_product_version_id"))
        batch_op.drop_index(op.f("ix_projects_tenant_id"))
        batch_op.drop_constraint(
            op.f("fk_projects_product_version_id_product_versions"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_projects_tenant_id_tenants"),
            type_="foreignkey",
        )
        batch_op.drop_column("product_version_id")
        batch_op.drop_column("tenant_id")
    for name in reversed(TABLES[:3]):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
