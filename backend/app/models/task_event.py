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
    )

    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(128), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    task = relationship("Task", back_populates="events")
