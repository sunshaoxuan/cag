"""Add active knowledge generation pointers.

Revision ID: 20260730_0016
Revises: 20260730_0015
Create Date: 2026-07-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_0016"
down_revision: str | Sequence[str] | None = "20260730_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        item["name"]
        for item in inspector.get_columns("knowledge_documents")
    }
    if "generation_ingestion_id" not in columns:
        op.add_column(
            "knowledge_documents",
            sa.Column(
                "generation_ingestion_id",
                sa.String(),
                nullable=True,
            ),
        )
    foreign_keys = inspector.get_foreign_keys("knowledge_documents")
    generation_foreign_key = next(
        (
            item
            for item in foreign_keys
            if "generation_ingestion_id"
            in item.get("constrained_columns", [])
        ),
        None,
    )
    foreign_key_name = "fk_kdoc_generation_ingestion"
    if (
        bind.dialect.name != "sqlite"
        and generation_foreign_key is None
    ):
        op.create_foreign_key(
            foreign_key_name,
            "knowledge_documents",
            "knowledge_ingestions",
            ["generation_ingestion_id"],
            ["id"],
            ondelete="SET NULL",
        )
    indexes = {
        item["name"]
        for item in inspector.get_indexes("knowledge_documents")
    }
    if "ix_knowledge_documents_generation_ingestion_id" not in indexes:
        op.create_index(
            "ix_knowledge_documents_generation_ingestion_id",
            "knowledge_documents",
            ["generation_ingestion_id"],
        )

    sources = bind.execute(
        sa.text("SELECT id FROM knowledge_sources")
    ).mappings()
    for source in sources:
        latest = bind.execute(
            sa.text(
                "SELECT id FROM knowledge_ingestions "
                "WHERE source_id = :source_id AND status = 'completed' "
                "ORDER BY completed_at DESC, created_at DESC LIMIT 1"
            ),
            {"source_id": source["id"]},
        ).scalar()
        if latest is None:
            continue
        bind.execute(
            sa.text(
                "UPDATE knowledge_documents "
                "SET generation_ingestion_id = :latest "
                "WHERE source_id = :source_id"
            ),
            {"latest": latest, "source_id": source["id"]},
        )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index(
        "ix_knowledge_documents_generation_ingestion_id",
        table_name="knowledge_documents",
    )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("knowledge_documents") as batch_op:
            batch_op.drop_column("generation_ingestion_id")
    else:
        generation_foreign_key = next(
            (
                item
                for item in sa.inspect(bind).get_foreign_keys(
                    "knowledge_documents"
                )
                if "generation_ingestion_id"
                in item.get("constrained_columns", [])
            ),
            None,
        )
        if generation_foreign_key is None:
            raise RuntimeError(
                "Knowledge generation foreign key is unavailable"
            )
        op.drop_constraint(
            generation_foreign_key["name"],
            "knowledge_documents",
            type_="foreignkey",
        )
        op.drop_column(
            "knowledge_documents",
            "generation_ingestion_id",
        )
