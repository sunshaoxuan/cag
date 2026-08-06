"""Add scoped customer ledger analysis records.

Revision ID: 20260806_0025
Revises: 20260806_0024
Create Date: 2026-08-06
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

from app.models import Base
from app.knowledge.customer_ledger_contracts import customer_ledger_schema_registry


revision: str = "20260806_0025"
down_revision: str | Sequence[str] | None = "20260806_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLES = [
    "knowledge_analysis_scopes",
    "knowledge_scope_ingestion_requests",
    "knowledge_document_versions",
    "knowledge_processing_versions",
    "knowledge_analysis_template_versions",
    "knowledge_extraction_tasks",
    "knowledge_extraction_task_events",
    "knowledge_extraction_task_documents",
    "knowledge_block_versions",
    "knowledge_block_applicabilities",
    "knowledge_field_candidates",
    "knowledge_candidate_evidence",
    "knowledge_field_conflicts",
]


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES[:1]:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)
    inspector = sa.inspect(bind)
    ingestion_columns = {
        item["name"] for item in inspector.get_columns("knowledge_ingestions")
    }
    ingestion_indexes = {
        item["name"] for item in inspector.get_indexes("knowledge_ingestions")
    }
    ingestion_foreign_keys = {
        item["name"] for item in inspector.get_foreign_keys("knowledge_ingestions")
    }
    with op.batch_alter_table("knowledge_ingestions") as batch_op:
        if "analysis_scope_id" not in ingestion_columns:
            batch_op.add_column(sa.Column("analysis_scope_id", sa.String(), nullable=True))
        if "scope_prefix" not in ingestion_columns:
            batch_op.add_column(sa.Column("scope_prefix", sa.Text(), nullable=True))
        if "retry_statuses" not in ingestion_columns:
            batch_op.add_column(
                sa.Column("retry_statuses", sa.JSON(), nullable=False, server_default="[]")
            )
        foreign_key_name = op.f(
            "fk_knowledge_ingestions_analysis_scope_id_knowledge_analysis_scopes"
        )
        if foreign_key_name not in ingestion_foreign_keys:
            batch_op.create_foreign_key(
                foreign_key_name,
                "knowledge_analysis_scopes",
                ["analysis_scope_id"],
                ["id"],
                ondelete="RESTRICT",
            )
        index_name = op.f("ix_knowledge_ingestions_analysis_scope_id")
        if index_name not in ingestion_indexes:
            batch_op.create_index(index_name, ["analysis_scope_id"])
    for name in TABLES[2:]:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)
    Base.metadata.tables[TABLES[1]].create(bind=bind, checkfirst=True)
    inspector = sa.inspect(bind)
    document_uniques = {
        item["name"] for item in inspector.get_unique_constraints("knowledge_documents")
    }
    document_indexes = {
        item["name"]: item for item in inspector.get_indexes("knowledge_documents")
    }
    with op.batch_alter_table("knowledge_documents") as batch_op:
        if "uq_knowledge_documents_source_entry_id" in document_uniques:
            batch_op.drop_constraint(
                "uq_knowledge_documents_source_entry_id", type_="unique"
            )
        source_entry_index = document_indexes.get(
            "ix_knowledge_documents_source_entry_id"
        )
        if source_entry_index and source_entry_index.get("unique"):
            batch_op.drop_index("ix_knowledge_documents_source_entry_id")
            batch_op.create_index(
                "ix_knowledge_documents_source_entry_id",
                ["source_entry_id"],
                unique=False,
            )
    template = sa.table(
        "knowledge_analysis_template_versions",
        sa.column("id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("field_contracts", sa.JSON()),
        sa.column("schema_registry", sa.JSON()),
        sa.column("source_priorities", sa.JSON()),
        sa.column("extractor_version", sa.String()),
        sa.column("enabled", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        template,
        [
            {
                "id": str(uuid4()),
                "code": "ORGANIZATION_PROFILE_ENRICHMENT",
                "version": 1,
                "field_contracts": [],
                "schema_registry": customer_ledger_schema_registry(),
                "source_priorities": [
                    {"pattern": "保守契約", "priority": 10},
                    {"pattern": "台帳", "priority": 20},
                    {"pattern": "導入システム一覧", "priority": 30},
                    {"pattern": "*", "priority": 100},
                ],
                "extractor_version": "customer-ledger-v1",
                "enabled": True,
                "created_at": datetime.now(timezone.utc),
            }
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES[1:]):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
    with op.batch_alter_table("knowledge_ingestions") as batch_op:
        batch_op.drop_index(op.f("ix_knowledge_ingestions_analysis_scope_id"))
        batch_op.drop_constraint(
            op.f("fk_knowledge_ingestions_analysis_scope_id_knowledge_analysis_scopes"),
            type_="foreignkey",
        )
        batch_op.drop_column("retry_statuses")
        batch_op.drop_column("scope_prefix")
        batch_op.drop_column("analysis_scope_id")
    Base.metadata.tables[TABLES[0]].drop(bind=bind, checkfirst=True)
