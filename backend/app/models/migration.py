from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PhysicalIdMixin, utc_now


class DataMigrationReceipt(PhysicalIdMixin, Base):
    __tablename__ = "data_migration_receipts"
    __table_args__ = (
        UniqueConstraint(
            "migration_key",
            name="uq_data_migration_receipts_migration_key",
        ),
    )

    migration_key: Mapped[str] = mapped_column(String(128), index=True)
    source_path: Mapped[str] = mapped_column(Text)
    source_sha256: Mapped[str] = mapped_column(String(64), index=True)
    target_revision: Mapped[str] = mapped_column(String(64))
    report_path: Mapped[str] = mapped_column(Text)
    verification: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
