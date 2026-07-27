"""add external API trace and global audit stream

Revision ID: 20260727_0008
Revises: 20260727_0007
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0008"
down_revision = "20260727_0007"
branch_labels = None
depends_on = None


AUDIT_CURSOR_ID = "00000000-0000-4000-8000-000000000008"


def upgrade() -> None:
    op.create_table(
        "audit_cursors",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("next_sequence", sa.Integer(), nullable=False),
        sa.UniqueConstraint("name", name="uq_audit_cursors_name"),
    )

    with op.batch_alter_table("tasks") as batch:
        batch.add_column(
            sa.Column(
                "trigger_source",
                sa.String(length=32),
                nullable=False,
                server_default="legacy",
            )
        )
        batch.add_column(
            sa.Column(
                "client_id",
                sa.String(length=128),
                nullable=False,
                server_default="legacy",
            )
        )
        batch.add_column(
            sa.Column(
                "client_request_id",
                sa.String(length=128),
                nullable=False,
                server_default="legacy",
            )
        )
        batch.add_column(
            sa.Column("idempotency_key", sa.String(length=255), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "request_hash",
                sa.String(length=64),
                nullable=False,
                server_default="legacy",
            )
        )
        batch.add_column(
            sa.Column(
                "request_metadata",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE tasks "
            "SET client_request_id = id, request_hash = 'legacy:' || id"
        )
    )

    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("trigger_source", server_default=None)
        batch.alter_column("client_id", server_default=None)
        batch.alter_column("client_request_id", server_default=None)
        batch.alter_column("request_hash", server_default=None)
        batch.alter_column("request_metadata", server_default=None)
        batch.create_unique_constraint(
            "uq_tasks_client_id_idempotency_key",
            ["client_id", "idempotency_key"],
        )
        batch.create_index(
            "ix_tasks_trigger_source",
            ["trigger_source"],
        )
        batch.create_index("ix_tasks_client_id", ["client_id"])
        batch.create_index(
            "ix_tasks_client_request_id",
            ["client_request_id"],
        )

    with op.batch_alter_table("task_events") as batch:
        batch.add_column(
            sa.Column("global_sequence", sa.Integer(), nullable=True)
        )

    event_rows = list(
        connection.execute(
            sa.text(
                "SELECT id FROM task_events "
                "ORDER BY timestamp ASC, task_id ASC, sequence ASC, id ASC"
            )
        )
    )
    for sequence, row in enumerate(event_rows, start=1):
        connection.execute(
            sa.text(
                "UPDATE task_events "
                "SET global_sequence = :sequence WHERE id = :event_id"
            ),
            {"sequence": sequence, "event_id": row[0]},
        )

    with op.batch_alter_table("task_events") as batch:
        batch.alter_column("global_sequence", nullable=False)
        batch.create_unique_constraint(
            "uq_task_events_global_sequence",
            ["global_sequence"],
        )
        batch.create_index(
            "ix_task_events_global_sequence",
            ["global_sequence"],
        )

    op.bulk_insert(
        sa.table(
            "audit_cursors",
            sa.column("id", sa.String()),
            sa.column("name", sa.String()),
            sa.column("next_sequence", sa.Integer()),
        ),
        [
            {
                "id": AUDIT_CURSOR_ID,
                "name": "gateway",
                "next_sequence": len(event_rows) + 1,
            }
        ],
    )


def downgrade() -> None:
    with op.batch_alter_table("task_events") as batch:
        batch.drop_index("ix_task_events_global_sequence")
        batch.drop_constraint(
            "uq_task_events_global_sequence",
            type_="unique",
        )
        batch.drop_column("global_sequence")

    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_client_request_id")
        batch.drop_index("ix_tasks_client_id")
        batch.drop_index("ix_tasks_trigger_source")
        batch.drop_constraint(
            "uq_tasks_client_id_idempotency_key",
            type_="unique",
        )
        batch.drop_column("request_metadata")
        batch.drop_column("request_hash")
        batch.drop_column("idempotency_key")
        batch.drop_column("client_request_id")
        batch.drop_column("client_id")
        batch.drop_column("trigger_source")

    op.drop_table("audit_cursors")
