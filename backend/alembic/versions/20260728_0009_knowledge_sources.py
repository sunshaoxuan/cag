"""add managed enterprise knowledge sources

Revision ID: 20260728_0009
Revises: 20260727_0008
"""

import hashlib

from alembic import op
import sqlalchemy as sa


revision = "20260728_0009"
down_revision = "20260727_0008"
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
    source_column_definitions = {
        "source_type": sa.Column(
            "source_type",
            sa.String(length=32),
            nullable=False,
            server_default="local_directory",
        ),
        "source_key": sa.Column(
            "source_key", sa.String(length=64), nullable=True
        ),
        "reference": sa.Column(
            "reference", sa.String(length=255), nullable=True
        ),
        "subpath": sa.Column("subpath", sa.Text(), nullable=True),
        "credential_ref": sa.Column(
            "credential_ref", sa.String(length=255), nullable=True
        ),
        "credential_username": sa.Column(
            "credential_username",
            sa.String(length=255),
            nullable=True,
        ),
        "enabled": sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        "last_validated_at": sa.Column(
            "last_validated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        "last_collected_at": sa.Column(
            "last_collected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    }
    for name, column in source_column_definitions.items():
        if name not in source_columns:
            op.add_column("knowledge_sources", column)
    if "duplicate_files" not in ingestion_columns:
        op.add_column(
            "knowledge_ingestions",
            sa.Column(
                "duplicate_files",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, project_id, root_path, scope "
            "FROM knowledge_sources ORDER BY created_at, id"
        )
    ).mappings()
    used: set[tuple[str, str]] = set()
    for row in rows:
        payload = "\n".join(
            (
                "local_directory",
                str(row["root_path"]).rstrip("/\\").casefold(),
                "",
                "",
                str(row["scope"]),
            )
        )
        source_key = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        identity = (str(row["project_id"]), source_key)
        if identity in used:
            source_key = hashlib.sha256(
                f"{payload}\nlegacy:{row['id']}".encode("utf-8")
            ).hexdigest()
            identity = (str(row["project_id"]), source_key)
        used.add(identity)
        connection.execute(
            sa.text(
                "UPDATE knowledge_sources "
                "SET source_key = :source_key WHERE id = :id"
            ),
            {"source_key": source_key, "id": row["id"]},
        )

    inspector = sa.inspect(op.get_bind())
    constraints = {
        item["name"]
        for item in inspector.get_unique_constraints("knowledge_sources")
    }
    indexes = {
        item["name"] for item in inspector.get_indexes("knowledge_sources")
    }
    source_key_nullable = next(
        column["nullable"]
        for column in inspector.get_columns("knowledge_sources")
        if column["name"] == "source_key"
    )
    with op.batch_alter_table("knowledge_sources") as batch:
        if source_key_nullable:
            batch.alter_column(
                "source_key",
                existing_type=sa.String(length=64),
                nullable=False,
            )
        if "uq_knowledge_sources_project_source_key" not in constraints:
            batch.create_unique_constraint(
                "uq_knowledge_sources_project_source_key",
                ["project_id", "source_key"],
            )
        if "ix_knowledge_sources_source_type" not in indexes:
            batch.create_index(
                "ix_knowledge_sources_source_type",
                ["source_type"],
            )
        if "ix_knowledge_sources_source_key" not in indexes:
            batch.create_index(
                "ix_knowledge_sources_source_key",
                ["source_key"],
            )
        if "ix_knowledge_sources_enabled" not in indexes:
            batch.create_index(
                "ix_knowledge_sources_enabled",
                ["enabled"],
            )


def downgrade() -> None:
    with op.batch_alter_table("knowledge_sources") as batch:
        batch.drop_index("ix_knowledge_sources_enabled")
        batch.drop_index("ix_knowledge_sources_source_key")
        batch.drop_index("ix_knowledge_sources_source_type")
        batch.drop_constraint(
            "uq_knowledge_sources_project_source_key",
            type_="unique",
        )
        batch.drop_column("last_collected_at")
        batch.drop_column("last_validated_at")
        batch.drop_column("enabled")
        batch.drop_column("credential_username")
        batch.drop_column("credential_ref")
        batch.drop_column("subpath")
        batch.drop_column("reference")
        batch.drop_column("source_key")
        batch.drop_column("source_type")
    op.drop_column("knowledge_ingestions", "duplicate_files")
