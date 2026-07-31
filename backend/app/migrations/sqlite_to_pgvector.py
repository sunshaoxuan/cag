from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    MetaData,
    create_engine,
    delete,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Connection, Engine, make_url

from app.models import Base


TARGET_ALEMBIC_REVISION = "20260731_0017"
ACTIVE_INGESTION_STATUSES = ("queued", "running")
ACTIVE_TASK_STATUSES = (
    "queued",
    "preparing",
    "running",
    "waiting_approval",
)
ALEMBIC_BOOTSTRAP_TABLES = {"audit_cursors"}


class MigrationBlockedError(RuntimeError):
    pass


@dataclass(frozen=True)
class TableReceipt:
    table: str
    source_rows: int
    target_rows: int | None
    source_id_sha256: str | None
    target_id_sha256: str | None


def redact_database_url(url: str) -> str:
    return make_url(url).render_as_string(hide_password=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sqlite_table_names(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )
    return [str(row[0]) for row in rows]


def inspect_sqlite_source(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MigrationBlockedError(f"SQLite source does not exist: {path}")
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise MigrationBlockedError(
                f"SQLite integrity check failed: {integrity}"
            )
        tables = sqlite_table_names(connection)
        active_ingestions: list[dict[str, str]] = []
        if "knowledge_ingestions" in tables:
            placeholders = ",".join("?" for _ in ACTIVE_INGESTION_STATUSES)
            rows = connection.execute(
                "SELECT id, status FROM knowledge_ingestions "
                f"WHERE status IN ({placeholders}) ORDER BY created_at",
                ACTIVE_INGESTION_STATUSES,
            )
            active_ingestions = [
                {"id": str(row[0]), "status": str(row[1])} for row in rows
            ]
        active_tasks: list[dict[str, str]] = []
        if "tasks" in tables:
            placeholders = ",".join("?" for _ in ACTIVE_TASK_STATUSES)
            rows = connection.execute(
                "SELECT id, status FROM tasks "
                f"WHERE status IN ({placeholders}) ORDER BY created_at",
                ACTIVE_TASK_STATUSES,
            )
            active_tasks = [
                {"id": str(row[0]), "status": str(row[1])} for row in rows
            ]
        table_counts = {
            table: int(
                connection.execute(
                    f'SELECT count(*) FROM "{table}"'
                ).fetchone()[0]
            )
            for table in tables
        }
        vector_count = 0
        vector_dimensions: list[int] = []
        if "knowledge_chunks" in tables:
            vector_count = int(
                connection.execute(
                    "SELECT count(*) FROM knowledge_chunks "
                    "WHERE embedding IS NOT NULL"
                ).fetchone()[0]
            )
            columns = {
                str(row[1])
                for row in connection.execute(
                    "PRAGMA table_info(knowledge_chunks)"
                )
            }
            if "embedding_dimensions" in columns:
                vector_dimensions = [
                    int(row[0])
                    for row in connection.execute(
                        "SELECT DISTINCT embedding_dimensions "
                        "FROM knowledge_chunks "
                        "WHERE embedding IS NOT NULL "
                        "ORDER BY embedding_dimensions"
                    )
                ]
        return {
            "integrity": integrity,
            "active_ingestions": active_ingestions,
            "active_tasks": active_tasks,
            "table_counts": table_counts,
            "vector_count": vector_count,
            "vector_dimensions": vector_dimensions,
        }
    finally:
        connection.close()


def create_consistent_snapshot(source: Path, target: Path) -> None:
    source_connection = sqlite3.connect(
        f"file:{source.as_posix()}?mode=ro",
        uri=True,
    )
    target_connection = sqlite3.connect(target)
    try:
        source_connection.backup(target_connection)
    finally:
        target_connection.close()
        source_connection.close()


def _id_digest(connection: Connection, table) -> str | None:
    if "id" not in table.c:
        return None
    digest = hashlib.sha256()
    for value in connection.scalars(select(table.c.id).order_by(table.c.id)):
        digest.update(str(value).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _target_preflight(engine: Engine) -> dict[str, Any]:
    if make_url(str(engine.url)).get_backend_name() != "postgresql":
        raise MigrationBlockedError(
            "Migration target must be PostgreSQL with pgvector."
        )
    with engine.connect() as connection:
        pgvector_version = connection.scalar(
            text(
                "SELECT extversion FROM pg_extension "
                "WHERE extname = 'vector'"
            )
        )
        if pgvector_version is None:
            raise MigrationBlockedError(
                "Target PostgreSQL does not have the vector extension."
            )
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        if "alembic_version" not in tables:
            raise MigrationBlockedError(
                "Target database has not been initialized by Alembic."
            )
        revision = connection.scalar(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        )
        if revision != TARGET_ALEMBIC_REVISION:
            raise MigrationBlockedError(
                "Target Alembic revision is "
                f"{revision!r}; expected {TARGET_ALEMBIC_REVISION!r}."
            )
        missing_tables = sorted(
            table.name
            for table in Base.metadata.sorted_tables
            if table.name not in tables
        )
        if missing_tables:
            raise MigrationBlockedError(
                "Target schema is incomplete: " + ", ".join(missing_tables)
            )
        return {
            "pgvector_version": str(pgvector_version),
            "alembic_revision": str(revision),
        }


def _batched(
    rows: Iterable[dict[str, Any]],
    batch_size: int,
) -> Iterable[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _copy_tables(
    source_engine: Engine,
    target_engine: Engine,
    *,
    batch_size: int,
    replace_target: bool = False,
) -> list[TableReceipt]:
    source_metadata = MetaData()
    source_metadata.reflect(bind=source_engine)
    source_tables = source_metadata.tables
    receipts: list[TableReceipt] = []
    with source_engine.connect() as source_connection:
        with target_engine.begin() as target_connection:
            if replace_target:
                for target_table in reversed(Base.metadata.sorted_tables):
                    target_connection.execute(delete(target_table))
            for target_table in Base.metadata.sorted_tables:
                source_table = source_tables.get(target_table.name)
                target_count = int(
                    target_connection.scalar(
                        select(func.count()).select_from(target_table)
                    )
                    or 0
                )
                if (
                    target_count
                    and target_table.name in ALEMBIC_BOOTSTRAP_TABLES
                ):
                    target_connection.execute(delete(target_table))
                    target_count = 0
                if source_table is None:
                    if target_count:
                        raise MigrationBlockedError(
                            f"Target table {target_table.name} is not empty."
                        )
                    receipts.append(
                        TableReceipt(
                            table=target_table.name,
                            source_rows=0,
                            target_rows=0,
                            source_id_sha256=None,
                            target_id_sha256=None,
                        )
                    )
                    continue
                source_count = int(
                    source_connection.scalar(
                        select(func.count()).select_from(source_table)
                    )
                    or 0
                )
                if target_count:
                    raise MigrationBlockedError(
                        f"Target table {target_table.name} is not empty."
                    )
                shared_columns = [
                    column.name
                    for column in target_table.columns
                    if column.name in source_table.c
                ]
                row_result = source_connection.execute(
                    select(*(source_table.c[name] for name in shared_columns))
                )
                mappings = (
                    {name: row._mapping[name] for name in shared_columns}
                    for row in row_result
                )
                for batch in _batched(mappings, batch_size):
                    target_connection.execute(target_table.insert(), batch)
                copied_count = int(
                    target_connection.scalar(
                        select(func.count()).select_from(target_table)
                    )
                    or 0
                )
                if copied_count != source_count:
                    raise MigrationBlockedError(
                        f"Row count mismatch for {target_table.name}: "
                        f"{source_count} source, {copied_count} target."
                    )
                receipts.append(
                    TableReceipt(
                        table=target_table.name,
                        source_rows=source_count,
                        target_rows=copied_count,
                        source_id_sha256=_id_digest(
                            source_connection,
                            source_table,
                        ),
                        target_id_sha256=_id_digest(
                            target_connection,
                            target_table,
                        ),
                    )
                )
            for receipt in receipts:
                if (
                    receipt.source_id_sha256 is not None
                    and receipt.source_id_sha256
                    != receipt.target_id_sha256
                ):
                    raise MigrationBlockedError(
                        f"Physical ID digest mismatch for {receipt.table}."
                    )
    return receipts


def _verify_vectors(engine: Engine) -> dict[str, Any]:
    with engine.connect() as connection:
        count = int(
            connection.scalar(
                text(
                    "SELECT count(*) FROM knowledge_chunks "
                    "WHERE embedding IS NOT NULL"
                )
            )
            or 0
        )
        dimensions = [
            int(value)
            for value in connection.scalars(
                text(
                    "SELECT DISTINCT vector_dims(embedding) "
                    "FROM knowledge_chunks "
                    "WHERE embedding IS NOT NULL "
                    "ORDER BY vector_dims(embedding)"
                )
            )
        ]
        index_present = bool(
            connection.scalar(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND indexname = "
                    "'ix_knowledge_chunks_embedding_hnsw'"
                    ")"
                )
            )
        )
        if not index_present:
            raise MigrationBlockedError(
                "pgvector HNSW index is missing after migration."
            )
        return {
            "vector_count": count,
            "vector_dimensions": dimensions,
            "hnsw_index_present": index_present,
        }


def _write_report(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "migration_report.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# SQLite to PostgreSQL pgvector migration report",
        "",
        f"Status: {report['status']}",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Source SHA256: `{report['source']['sha256']}`",
        "",
        f"Target: `{report['target']['url']}`",
        "",
        f"Mode: {report['mode']}",
        "",
        "## Vector verification",
        "",
        f"* Source vectors: {report['source']['vector_count']}",
        f"* Source dimensions: {report['source']['vector_dimensions']}",
        f"* Target vectors: {report['target'].get('vector_count')}",
        f"* Target dimensions: {report['target'].get('vector_dimensions')}",
        f"* HNSW index present: {report['target'].get('hnsw_index_present')}",
        "",
        "## Table receipts",
        "",
        "| Table | Source rows | Target rows | Physical ID digest |",
        "|---|---:|---:|---|",
    ]
    for item in report.get("tables", []):
        digest_status = (
            "match"
            if item["source_id_sha256"] == item["target_id_sha256"]
            else "n/a"
        )
        lines.append(
            f"| {item['table']} | {item['source_rows']} | "
            f"{item['target_rows']} | {digest_status} |"
        )
    (output_dir / "migration_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def migrate(
    *,
    source_path: Path,
    target_url: str,
    output_dir: Path,
    apply: bool,
    batch_size: int = 500,
    replace_target: bool = False,
) -> dict[str, Any]:
    source_path = source_path.resolve()
    source = inspect_sqlite_source(source_path)
    report: dict[str, Any] = {
        "status": "preflight_passed",
        "mode": (
            "replace_target"
            if apply and replace_target
            else "apply"
            if apply
            else "dry_run"
        ),
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {
            "path": str(source_path),
            "sha256": sha256_file(source_path),
            **source,
        },
        "target": {
            "url": redact_database_url(target_url),
        },
        "tables": [],
    }
    if source["active_ingestions"]:
        active = ", ".join(
            f"{item['id']}:{item['status']}"
            for item in source["active_ingestions"]
        )
        error = (
            "SQLite source still has active knowledge ingestions: " + active
        )
        report["status"] = "blocked"
        report["error"] = error
        _write_report(output_dir, report)
        raise MigrationBlockedError(error)
    if source["active_tasks"]:
        active = ", ".join(
            f"{item['id']}:{item['status']}"
            for item in source["active_tasks"]
        )
        error = "SQLite source still has active tasks: " + active
        report["status"] = "blocked"
        report["error"] = error
        _write_report(output_dir, report)
        raise MigrationBlockedError(error)
    target_engine = create_engine(target_url, pool_pre_ping=True)
    snapshot_path = output_dir / ".source-snapshot.sqlite"
    try:
        report["target"].update(_target_preflight(target_engine))
        if apply:
            output_dir.mkdir(parents=True, exist_ok=True)
            create_consistent_snapshot(source_path, snapshot_path)
            snapshot_engine = create_engine(
                f"sqlite+pysqlite:///{snapshot_path.as_posix()}"
            )
            try:
                receipts = _copy_tables(
                    snapshot_engine,
                    target_engine,
                    batch_size=batch_size,
                    replace_target=replace_target,
                )
            finally:
                snapshot_engine.dispose()
            report["tables"] = [asdict(item) for item in receipts]
            report["target"].update(_verify_vectors(target_engine))
            if (
                report["source"]["vector_count"]
                != report["target"]["vector_count"]
            ):
                raise MigrationBlockedError(
                    "Vector count differs between source and target."
                )
            report["status"] = "completed"
        _write_report(output_dir, report)
        return report
    except Exception as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        _write_report(output_dir, report)
        raise
    finally:
        target_engine.dispose()
        if snapshot_path.exists():
            snapshot_path.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate a completed One Agent Gateway SQLite database to "
            "PostgreSQL with pgvector."
        )
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--replace-target", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    target_url = os.environ.get("AGENT_GATEWAY_MIGRATION_TARGET_URL")
    if not target_url:
        raise SystemExit(
            "AGENT_GATEWAY_MIGRATION_TARGET_URL is required."
        )
    try:
        report = migrate(
            source_path=arguments.source,
            target_url=target_url,
            output_dir=arguments.output_dir,
            apply=arguments.apply,
            batch_size=arguments.batch_size,
            replace_target=arguments.replace_target,
        )
    except MigrationBlockedError as error:
        print(f"Migration blocked: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
