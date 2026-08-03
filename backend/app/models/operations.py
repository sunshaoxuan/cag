from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PhysicalIdMixin, utc_now


class OperationalIssueStatus:
    DETECTED = "detected"
    TRIAGING = "triaging"
    WAITING_APPROVAL = "waiting_approval"
    PLAN_REVISION_REQUIRED = "plan_revision_required"
    WAITING_EXTERNAL = "waiting_external"
    IMPLEMENTING = "implementing"
    EVALUATING = "evaluating"
    CLOSED = "closed"
    REJECTED = "rejected"
    VALIDATION_COMPLETED = "validation_completed"
    OUT_OF_SCOPE = "out_of_scope"
    TRIAGE_FAILED = "triage_failed"

    ACTIVE = {
        DETECTED,
        TRIAGING,
        WAITING_APPROVAL,
        PLAN_REVISION_REQUIRED,
        WAITING_EXTERNAL,
        IMPLEMENTING,
        EVALUATING,
        TRIAGE_FAILED,
    }
    TERMINAL = {CLOSED, REJECTED, VALIDATION_COMPLETED, OUT_OF_SCOPE}
    REOPENABLE = {
        CLOSED,
        REJECTED,
        VALIDATION_COMPLETED,
        OUT_OF_SCOPE,
        TRIAGE_FAILED,
        PLAN_REVISION_REQUIRED,
    }
    REJECTABLE = {
        WAITING_APPROVAL,
        PLAN_REVISION_REQUIRED,
        TRIAGE_FAILED,
        WAITING_EXTERNAL,
    }


class OperationalIssue(PhysicalIdMixin, Base):
    __tablename__ = "operational_issues"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "fingerprint",
            name="uq_operational_issues_project_fingerprint",
        ),
        UniqueConstraint("code", name="uq_operational_issues_code"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"),
        index=True,
    )
    parent_issue_id: Mapped[str | None] = mapped_column(
        ForeignKey("operational_issues.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    implementation_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(32), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    boundary: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    boundary_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolution_mode: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    resolution_mode_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    resolution_mode_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    decision_brief: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    review_recommendation: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )
    blocking_finding_count: Mapped[int] = mapped_column(Integer, default=0)
    event_sequence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(32),
        default=OperationalIssueStatus.DETECTED,
        index=True,
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    allowed_actions: Mapped[list[str]] = mapped_column(JSON, default=list)
    required_human_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_status: Mapped[str] = mapped_column(
        String(32),
        default="not_requested",
        index=True,
    )
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    improvement_branch: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    evaluation_status: Mapped[str] = mapped_column(
        String(32),
        default="not_started",
        index=True,
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class OperationalIssueOccurrence(PhysicalIdMixin, Base):
    __tablename__ = "operational_issue_occurrences"
    __table_args__ = (
        UniqueConstraint(
            "external_event_id",
            name="uq_operational_issue_occurrences_external_event_id",
        ),
    )

    issue_id: Mapped[str] = mapped_column(
        ForeignKey("operational_issues.id", ondelete="CASCADE"),
        index=True,
    )
    external_event_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )


class OperationalIssueArtifact(PhysicalIdMixin, Base):
    __tablename__ = "operational_issue_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "issue_id",
            "artifact_type",
            "revision",
            name="uq_operational_issue_artifacts_revision",
        ),
    )

    issue_id: Mapped[str] = mapped_column(
        ForeignKey("operational_issues.id", ondelete="CASCADE"),
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(64), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class OperationalIssueEvent(PhysicalIdMixin, Base):
    __tablename__ = "operational_issue_events"
    __table_args__ = (
        UniqueConstraint(
            "issue_id",
            "sequence",
            name="uq_operational_issue_events_sequence",
        ),
    )

    issue_id: Mapped[str] = mapped_column(
        ForeignKey("operational_issues.id", ondelete="CASCADE"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(64), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
