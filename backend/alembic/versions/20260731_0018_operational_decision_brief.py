"""Add operational decision classification and reviewer brief.

Revision ID: 20260731_0018
Revises: 20260731_0017
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260731_0018"
down_revision: str | Sequence[str] | None = "20260731_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operational_issues",
        sa.Column("resolution_mode", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "operational_issues",
        sa.Column("resolution_mode_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "operational_issues",
        sa.Column("resolution_mode_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "operational_issues",
        sa.Column(
            "decision_brief",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "operational_issues",
        sa.Column("review_recommendation", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "operational_issues",
        sa.Column(
            "blocking_finding_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "operational_issues",
        sa.Column(
            "event_sequence",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_index(
        op.f("ix_operational_issues_resolution_mode"),
        "operational_issues",
        ["resolution_mode"],
    )
    op.create_index(
        op.f("ix_operational_issues_review_recommendation"),
        "operational_issues",
        ["review_recommendation"],
    )

    op.execute(
        """
        UPDATE operational_issues
        SET event_sequence = COALESCE(
            (
                SELECT MAX(event.sequence)
                FROM operational_issue_events event
                WHERE event.issue_id = operational_issues.id
            ),
            0
        )
        """
    )
    op.execute(
        """
        UPDATE operational_issues
        SET resolution_mode = CASE
                WHEN boundary = 'cag_internal'
                    THEN 'agent_self_improvement'
                WHEN boundary IN (
                    'external_dependency',
                    'credential_or_authorization'
                )
                    THEN 'external_operator_action'
                WHEN boundary = 'policy_or_scope'
                    THEN 'out_of_scope'
                ELSE 'undetermined'
            END,
            resolution_mode_confidence = COALESCE(
                boundary_confidence,
                0.5
            ),
            resolution_mode_reason = CASE
                WHEN boundary = 'cag_internal'
                    THEN 'CAG internal changes can enter the governed Agent self-improvement workflow after administrator approval.'
                WHEN boundary IN (
                    'external_dependency',
                    'credential_or_authorization'
                )
                    THEN 'An authorized operator or external owner must complete the required action.'
                WHEN boundary = 'policy_or_scope'
                    THEN 'The issue is outside the CAG implementation boundary.'
                ELSE 'The available evidence is insufficient to select an implementation route.'
            END
        """
    )
    op.execute(
        """
        UPDATE operational_issues
        SET status = 'plan_revision_required',
            approval_status = 'revision_required',
            review_recommendation = 'revise',
            blocking_finding_count = 1
        WHERE status = 'waiting_approval'
          AND EXISTS (
              SELECT 1
              FROM operational_issue_artifacts artifact
              WHERE artifact.issue_id = operational_issues.id
                AND artifact.artifact_type = 'review'
                AND (
                    lower(CAST(artifact.content AS TEXT))
                        LIKE '%do_not_approve%'
                    OR lower(CAST(artifact.content AS TEXT))
                        LIKE '%reject_pending_revision%'
                    OR lower(CAST(artifact.content AS TEXT))
                        LIKE '%"recommendation": "revise"%'
                )
          )
        """
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_operational_issues_review_recommendation"),
        table_name="operational_issues",
    )
    op.drop_index(
        op.f("ix_operational_issues_resolution_mode"),
        table_name="operational_issues",
    )
    op.drop_column("operational_issues", "blocking_finding_count")
    op.drop_column("operational_issues", "review_recommendation")
    op.drop_column("operational_issues", "decision_brief")
    op.drop_column("operational_issues", "event_sequence")
    op.drop_column("operational_issues", "resolution_mode_reason")
    op.drop_column("operational_issues", "resolution_mode_confidence")
    op.drop_column("operational_issues", "resolution_mode")
