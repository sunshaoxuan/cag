"""Add idempotency metadata to conversations."""

from alembic import op
import sqlalchemy as sa


revision = "20260810_0026"
down_revision = "20260806_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("conversations") as batch:
        batch.add_column(
            sa.Column("client_id", sa.String(length=128), nullable=True)
        )
        batch.add_column(
            sa.Column("idempotency_key", sa.String(length=255), nullable=True)
        )
        batch.add_column(
            sa.Column("request_hash", sa.String(length=64), nullable=True)
        )
        batch.create_index("ix_conversations_client_id", ["client_id"])
        batch.create_unique_constraint(
            "uq_conversations_client_id_idempotency_key",
            ["client_id", "idempotency_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("conversations") as batch:
        batch.drop_constraint(
            "uq_conversations_client_id_idempotency_key",
            type_="unique",
        )
        batch.drop_index("ix_conversations_client_id")
        batch.drop_column("request_hash")
        batch.drop_column("idempotency_key")
        batch.drop_column("client_id")
