from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url

from app.config import Settings, get_settings
from app.migrations.sqlite_to_pgvector import (
    TARGET_ALEMBIC_REVISION,
    inspect_sqlite_source,
    migrate,
    sha256_file,
)
from app.models import DataMigrationReceipt


MIGRATION_KEY = "legacy-sqlite-to-postgresql-pgvector"


def run_auto_cutover(settings: Settings) -> dict[str, object]:
    target_backend = make_url(settings.database_url).get_backend_name()
    source_path = settings.legacy_sqlite_path.resolve()
    if not settings.auto_migrate_legacy_sqlite:
        return {"status": "disabled"}
    if target_backend != "postgresql":
        return {"status": "skipped", "reason": "target_is_not_postgresql"}
    if not source_path.is_file():
        return {"status": "skipped", "reason": "legacy_source_absent"}

    source_sha256 = sha256_file(source_path)
    target_engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with target_engine.connect() as connection:
            receipt = connection.execute(
                select(
                    DataMigrationReceipt.source_sha256,
                    DataMigrationReceipt.report_path,
                ).where(
                    DataMigrationReceipt.migration_key == MIGRATION_KEY
                )
            ).first()
        if receipt is not None and receipt.source_sha256 == source_sha256:
            return {
                "status": "already_completed",
                "source_sha256": source_sha256,
                "report_path": receipt.report_path,
            }

        source = inspect_sqlite_source(source_path)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output_dir = (
            settings.migration_receipt_root
            / f"auto-{timestamp}-{source_sha256[:12]}"
        )
        report = migrate(
            source_path=source_path,
            target_url=settings.database_url,
            output_dir=output_dir,
            apply=True,
            replace_target=True,
        )
        verification = {
            "source_table_counts": source["table_counts"],
            "source_vector_count": source["vector_count"],
            "target_vector_count": report["target"]["vector_count"],
            "physical_id_receipts": len(report["tables"]),
        }
        with target_engine.begin() as connection:
            connection.execute(
                DataMigrationReceipt.__table__.insert().values(
                    id=str(uuid4()),
                    migration_key=MIGRATION_KEY,
                    source_path=str(source_path),
                    source_sha256=source_sha256,
                    target_revision=TARGET_ALEMBIC_REVISION,
                    report_path=str(output_dir.resolve()),
                    verification=verification,
                    applied_at=datetime.now(UTC),
                )
            )
        return {
            "status": "completed",
            "source_sha256": source_sha256,
            "report_path": str(output_dir.resolve()),
            "verification": verification,
        }
    finally:
        target_engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description=(
            "Run the guarded legacy SQLite to PostgreSQL pgvector cutover."
        )
    )


def main() -> int:
    build_parser().parse_args()
    result = run_auto_cutover(get_settings())
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
