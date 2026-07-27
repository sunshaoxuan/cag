"""Add durable conversation event sequencing.

Revision ID: 20260727_0004
Revises: 20260727_0003
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260727_0004"
down_revision: str | Sequence[str] | None = "20260727_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("next_event_sequence", sa.Integer(), nullable=False, server_default="1"),
    )
    with op.batch_alter_table("task_events") as batch_op:
        batch_op.add_column(
            sa.Column("conversation_id", sa.String(), nullable=True),
        )
        batch_op.add_column(
            sa.Column("conversation_sequence", sa.Integer(), nullable=True),
        )
        batch_op.create_foreign_key(
            op.f("fk_task_events_conversation_id_conversations"),
            "conversations",
            ["conversation_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            op.f("ix_task_events_conversation_id"),
            ["conversation_id"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_task_events_conversation_id_sequence",
            ["conversation_id", "conversation_sequence"],
        )


def downgrade() -> None:
    with op.batch_alter_table("task_events") as batch_op:
        batch_op.drop_constraint(
            "uq_task_events_conversation_id_sequence",
            type_="unique",
        )
        batch_op.drop_index(op.f("ix_task_events_conversation_id"))
        batch_op.drop_constraint(
            op.f("fk_task_events_conversation_id_conversations"),
            type_="foreignkey",
        )
        batch_op.drop_column("conversation_sequence")
        batch_op.drop_column("conversation_id")
    op.drop_column("conversations", "next_event_sequence")
