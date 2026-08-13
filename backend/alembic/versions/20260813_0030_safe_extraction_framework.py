"""Add safe extraction probe and failure audit fields."""

from alembic import op
import sqlalchemy as sa


revision = "20260813_0030"
down_revision = "20260813_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("knowledge_source_entries") as batch:
        batch.alter_column(
            "extractor_version",
            type_=sa.String(length=64),
            existing_type=sa.String(length=32),
        )
    for table in ("knowledge_source_entries", "knowledge_ingestion_rejections"):
        op.add_column(table, sa.Column("retryable", sa.Boolean(), server_default=sa.false(), nullable=False))
        op.add_column(table, sa.Column("detected_mime", sa.String(length=255), nullable=True))
        op.add_column(table, sa.Column("detected_magic", sa.String(length=64), nullable=True))
    op.add_column("knowledge_source_entries", sa.Column("text_probability", sa.Float(), nullable=True))
    op.add_column("knowledge_ingestion_rejections", sa.Column("extractor_version", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_ingestion_rejections", "extractor_version")
    op.drop_column("knowledge_source_entries", "text_probability")
    for table in ("knowledge_ingestion_rejections", "knowledge_source_entries"):
        op.drop_column(table, "detected_magic")
        op.drop_column(table, "detected_mime")
        op.drop_column(table, "retryable")
    with op.batch_alter_table("knowledge_source_entries") as batch:
        batch.alter_column(
            "extractor_version",
            type_=sa.String(length=32),
            existing_type=sa.String(length=64),
        )
