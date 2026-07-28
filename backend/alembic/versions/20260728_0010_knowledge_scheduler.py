"""add durable knowledge source scheduling

Revision ID: 20260728_0010
Revises: 20260728_0009
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0010"
down_revision = "20260728_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    source_columns = {
        column["name"]
        for column in inspector.get_columns("knowledge_sources")
    }
    ingestion_columns = {
        column["name"]
        for column in inspector.get_columns("knowledge_ingestions")
    }
    source_definitions = {
        "sync_mode": sa.Column(
            "sync_mode",
            sa.String(length=32),
            nullable=False,
            server_default="manual",
        ),
        "sync_interval_minutes": sa.Column(
            "sync_interval_minutes",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
        "next_sync_at": sa.Column(
            "next_sync_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        "last_sync_attempt_at": sa.Column(
            "last_sync_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        "last_content_change_at": sa.Column(
            "last_content_change_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        "consecutive_failures": sa.Column(
            "consecutive_failures",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        "sync_lease_owner": sa.Column(
            "sync_lease_owner",
            sa.String(length=255),
            nullable=True,
        ),
        "sync_lease_expires_at": sa.Column(
            "sync_lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    }
    ingestion_definitions = {
        "changed_files": sa.Column(
            "changed_files",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        "removed_files": sa.Column(
            "removed_files",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        "trigger": sa.Column(
            "trigger",
            sa.String(length=32),
            nullable=False,
            server_default="manual",
        ),
        "started_at": sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    }
    for name, column in source_definitions.items():
        if name not in source_columns:
            op.add_column("knowledge_sources", column)
    for name, column in ingestion_definitions.items():
        if name not in ingestion_columns:
            op.add_column("knowledge_ingestions", column)

    inspector = sa.inspect(op.get_bind())
    source_indexes = {
        item["name"] for item in inspector.get_indexes("knowledge_sources")
    }
    ingestion_indexes = {
        item["name"]
        for item in inspector.get_indexes("knowledge_ingestions")
    }
    with op.batch_alter_table("knowledge_sources") as batch:
        if "ix_knowledge_sources_sync_mode" not in source_indexes:
            batch.create_index(
                "ix_knowledge_sources_sync_mode",
                ["sync_mode"],
            )
        if "ix_knowledge_sources_next_sync_at" not in source_indexes:
            batch.create_index(
                "ix_knowledge_sources_next_sync_at",
                ["next_sync_at"],
            )
        if (
            "ix_knowledge_sources_sync_lease_expires_at"
            not in source_indexes
        ):
            batch.create_index(
                "ix_knowledge_sources_sync_lease_expires_at",
                ["sync_lease_expires_at"],
            )
    if "ix_knowledge_ingestions_trigger" not in ingestion_indexes:
        with op.batch_alter_table("knowledge_ingestions") as batch:
            batch.create_index(
                "ix_knowledge_ingestions_trigger",
                ["trigger"],
            )


def downgrade() -> None:
    with op.batch_alter_table("knowledge_ingestions") as batch:
        batch.drop_index("ix_knowledge_ingestions_trigger")
        batch.drop_column("started_at")
        batch.drop_column("trigger")
        batch.drop_column("removed_files")
        batch.drop_column("changed_files")
    with op.batch_alter_table("knowledge_sources") as batch:
        batch.drop_index("ix_knowledge_sources_sync_lease_expires_at")
        batch.drop_index("ix_knowledge_sources_next_sync_at")
        batch.drop_index("ix_knowledge_sources_sync_mode")
        batch.drop_column("sync_lease_expires_at")
        batch.drop_column("sync_lease_owner")
        batch.drop_column("consecutive_failures")
        batch.drop_column("last_content_change_at")
        batch.drop_column("last_sync_attempt_at")
        batch.drop_column("next_sync_at")
        batch.drop_column("sync_interval_minutes")
        batch.drop_column("sync_mode")
