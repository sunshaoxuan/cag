"""add durable knowledge ingestion rejection audit

Revision ID: 20260729_0012
Revises: 20260728_0011
"""

from alembic import op
import sqlalchemy as sa


revision = "20260729_0012"
down_revision = "20260728_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    ingestion_columns = {
        item["name"]
        for item in inspector.get_columns("knowledge_ingestions")
    }
    columns = (
        sa.Column(
            "skipped_files",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "rejection_archive_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "rejection_archive_sha256",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "rejection_archive_created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    with op.batch_alter_table("knowledge_ingestions") as batch:
        for column in columns:
            if column.name not in ingestion_columns:
                batch.add_column(column)

    if "knowledge_ingestion_rejections" in inspector.get_table_names():
        return
    op.create_table(
        "knowledge_ingestion_rejections",
        sa.Column("ingestion_id", sa.String(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column(
            "entry_kind",
            sa.String(length=32),
            nullable=False,
            server_default="file",
        ),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column(
            "extension",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column(
            "extractor",
            sa.String(length=64),
            nullable=False,
            server_default="filesystem",
        ),
        sa.Column("error_type", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["knowledge_ingestions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ingestion_id",
            "relative_path",
            name="uq_knowledge_ingestion_rejections_ingestion_path",
        ),
    )
    for name in (
        "ingestion_id",
        "entry_kind",
        "disposition",
        "extension",
        "reason_code",
        "created_at",
    ):
        op.create_index(
            f"ix_knowledge_ingestion_rejections_{name}",
            "knowledge_ingestion_rejections",
            [name],
        )


def downgrade() -> None:
    op.drop_table("knowledge_ingestion_rejections")
    with op.batch_alter_table("knowledge_ingestions") as batch:
        batch.drop_column("rejection_archive_created_at")
        batch.drop_column("rejection_archive_sha256")
        batch.drop_column("rejection_archive_name")
        batch.drop_column("skipped_files")
