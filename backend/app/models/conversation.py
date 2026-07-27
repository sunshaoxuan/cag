from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PhysicalIdMixin, utc_now


class Conversation(PhysicalIdMixin, Base):
    __tablename__ = "conversations"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"),
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    codex_thread_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )
    next_event_sequence: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )

    project = relationship("Project", back_populates="conversations")
    tasks = relationship("Task", back_populates="conversation")
    events = relationship("TaskEvent", back_populates="conversation")
