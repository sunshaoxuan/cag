from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PhysicalIdMixin, utc_now


class CapabilityAsset(PhysicalIdMixin, Base):
    __tablename__ = "capability_assets"

    kind: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="proposed", index=True)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(128), default="learning-pipeline")
    shadow_runs: Mapped[int] = mapped_column(Integer, default=0)
    canary_runs: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    rolling_quality_delta: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class CapabilityEvaluation(PhysicalIdMixin, Base):
    __tablename__ = "capability_evaluations"

    asset_id: Mapped[str] = mapped_column(
        ForeignKey("capability_assets.id", ondelete="CASCADE"), index=True
    )
    stage: Mapped[str] = mapped_column(String(32), index=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    replay_count: Mapped[int] = mapped_column(Integer, default=0)
    project_coverage: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CapabilityPromotion(PhysicalIdMixin, Base):
    __tablename__ = "capability_promotions"

    asset_id: Mapped[str] = mapped_column(
        ForeignKey("capability_assets.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    decision: Mapped[str] = mapped_column(String(32), index=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    receipt_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CapabilityRollback(PhysicalIdMixin, Base):
    __tablename__ = "capability_rollbacks"

    asset_id: Mapped[str] = mapped_column(
        ForeignKey("capability_assets.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(Text)
    previous_status: Mapped[str] = mapped_column(String(32))
    restored_status: Mapped[str] = mapped_column(String(32), default="benchmarked")
    receipt_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class GardenerRun(PhysicalIdMixin, Base):
    __tablename__ = "gardener_runs"

    gardener: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    actions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class StandardControl(PhysicalIdMixin, Base):
    __tablename__ = "standard_controls"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    framework: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    implementation_status: Mapped[str] = mapped_column(String(32), index=True)
    control_mapping: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    evidence_paths: Mapped[list[str]] = mapped_column(JSON, default=list)
    certification_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
