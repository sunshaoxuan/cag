from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PhysicalIdMixin, utc_now


class Project(PhysicalIdMixin, Base):
    __tablename__ = "projects"

    code: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    repository_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )

    conversations = relationship("Conversation", back_populates="project")
    tasks = relationship("Task", back_populates="project")
