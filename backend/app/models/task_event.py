from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PhysicalIdMixin, utc_now


class TaskEvent(PhysicalIdMixin, Base):
    __tablename__ = "task_events"
    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "sequence",
            name="uq_task_events_task_id_sequence",
        ),
        UniqueConstraint(
            "conversation_id",
            "conversation_sequence",
            name="uq_task_events_conversation_id_sequence",
        ),
        UniqueConstraint(
            "global_sequence",
            name="uq_task_events_global_sequence",
        ),
    )

    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    global_sequence: Mapped[int] = mapped_column(Integer, index=True)
    conversation_sequence: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(128), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    task = relationship("Task", back_populates="events")
    conversation = relationship("Conversation", back_populates="events")


class AuditCursor(PhysicalIdMixin, Base):
    __tablename__ = "audit_cursors"

    name: Mapped[str] = mapped_column(String(64), unique=True)
    next_sequence: Mapped[int] = mapped_column(Integer, default=1)
