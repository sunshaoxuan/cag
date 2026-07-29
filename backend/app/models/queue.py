from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PhysicalIdMixin, utc_now


class QueueItemStatus:
    QUEUED = "queued"
    LEASED = "leased"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    TERMINAL = {COMPLETED, FAILED, CANCELLED}


class QueueItem(PhysicalIdMixin, Base):
    __tablename__ = "queue_items"
    __table_args__ = (
        CheckConstraint(
            "(task_id IS NOT NULL AND ingestion_id IS NULL) OR "
            "(task_id IS NULL AND ingestion_id IS NOT NULL)",
            name="exactly_one_resource",
        ),
        UniqueConstraint("task_id", name="uq_queue_items_task_id"),
        UniqueConstraint("ingestion_id", name="uq_queue_items_ingestion_id"),
        Index(
            "ix_queue_items_claim",
            "queue_name",
            "status",
            "available_at",
            "priority",
            "created_at",
        ),
    )

    queue_name: Mapped[str] = mapped_column(String(64), index=True)
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
    )
    ingestion_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_ingestions.id", ondelete="CASCADE"),
        nullable=True,
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"),
        index=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    client_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(
        String(32),
        default=QueueItemStatus.QUEUED,
        index=True,
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    lease_owner: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class QueueWorker(PhysicalIdMixin, Base):
    __tablename__ = "queue_workers"
    __table_args__ = (
        UniqueConstraint("worker_key", name="uq_queue_workers_worker_key"),
    )

    worker_key: Mapped[str] = mapped_column(String(255))
    queue_name: Mapped[str] = mapped_column(String(64), index=True)
    hostname: Mapped[str] = mapped_column(String(255))
    process_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="starting", index=True)
    current_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("queue_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
