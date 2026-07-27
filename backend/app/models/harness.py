from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PhysicalIdMixin, utc_now


class HarnessRun(PhysicalIdMixin, Base):
    __tablename__ = "harness_runs"

    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, index=True
    )
    profile: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    max_parallel: Mapped[int] = mapped_column(Integer, default=1)
    task_contract: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class HarnessProfile(PhysicalIdMixin, Base):
    __tablename__ = "harness_profiles"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(32), default="1")
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AgentRun(PhysicalIdMixin, Base):
    __tablename__ = "agent_runs"

    harness_run_id: Mapped[str] = mapped_column(
        ForeignKey("harness_runs.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    run_key: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(64), index=True)
    phase: Mapped[str] = mapped_column(String(32), index=True)
    access_mode: Mapped[str] = mapped_column(String(32), default="read_only")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    budget_seconds: Mapped[int] = mapped_column(Integer, default=900)
    runtime_thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TaskGraphNode(PhysicalIdMixin, Base):
    __tablename__ = "task_graph_nodes"

    harness_run_id: Mapped[str] = mapped_column(
        ForeignKey("harness_runs.id", ondelete="CASCADE"), index=True
    )
    node_key: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(64))
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="queued")


class AgentArtifact(PhysicalIdMixin, Base):
    __tablename__ = "agent_artifacts"

    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(64), index=True)
    schema_version: Mapped[str] = mapped_column(String(32), default="1")
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ReviewFinding(PhysicalIdMixin, Base):
    __tablename__ = "review_findings"

    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    severity: Mapped[str] = mapped_column(String(32), default="info", index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False)


class VerificationRun(PhysicalIdMixin, Base):
    __tablename__ = "verification_runs"

    harness_run_id: Mapped[str] = mapped_column(
        ForeignKey("harness_runs.id", ondelete="CASCADE"), index=True
    )
    validator: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), index=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class QualityScore(PhysicalIdMixin, Base):
    __tablename__ = "quality_scores"

    harness_run_id: Mapped[str] = mapped_column(
        ForeignKey("harness_runs.id", ondelete="CASCADE"), index=True
    )
    overall: Mapped[float] = mapped_column(Float)
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LearningSignal(PhysicalIdMixin, Base):
    __tablename__ = "learning_signals"

    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    signal_type: Mapped[str] = mapped_column(String(64), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ApprovalRequest(PhysicalIdMixin, Base):
    __tablename__ = "approval_requests"

    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    request_type: Mapped[str] = mapped_column(String(64), index=True)
    subject: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    policy_decision: Mapped[str] = mapped_column(String(32))
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
