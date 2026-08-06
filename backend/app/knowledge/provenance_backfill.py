from __future__ import annotations

import argparse
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath

from sqlalchemy import select

from app.config import get_settings
from app.database import Database
from app.models import KnowledgeSource, KnowledgeSourceEntry


ProgressSink = Callable[[dict[str, int]], None]


@dataclass(frozen=True)
class PendingFile:
    id: str
    relative_path: str
    file_size: int
    modified_at: datetime


@dataclass(frozen=True)
class HashResult:
    item: PendingFile
    raw_content_hash: str | None
    status: str


def _physical_path(root: Path, relative_path: str) -> Path:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ValueError("Source entry path is not a safe relative path")
    return root.joinpath(*relative.parts)


def _utc_modified_at(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _normalized_modified_at(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_file(root: Path, item: PendingFile) -> HashResult:
    try:
        path = _physical_path(root, item.relative_path)
        if path.is_symlink():
            return HashResult(item, None, "unsafe_path")
        before = path.stat()
        if (
            before.st_size != item.file_size
            or _utc_modified_at(before.st_mtime)
            != _normalized_modified_at(item.modified_at)
        ):
            return HashResult(item, None, "source_changed")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        after = path.stat()
        if (
            after.st_size != before.st_size
            or after.st_mtime_ns != before.st_mtime_ns
        ):
            return HashResult(item, None, "source_changed")
        return HashResult(item, digest.hexdigest(), "hashed")
    except (OSError, ValueError):
        return HashResult(item, None, "read_failed")


def backfill_raw_content_hashes(
    database: Database,
    source_id: str,
    *,
    workers: int = 8,
    batch_size: int = 200,
    progress: ProgressSink | None = None,
) -> dict[str, int]:
    if workers < 1 or workers > 32:
        raise ValueError("workers must be between 1 and 32")
    if batch_size < 1 or batch_size > 2_000:
        raise ValueError("batch_size must be between 1 and 2000")

    with database.session_factory() as session:
        source = session.get(KnowledgeSource, source_id)
        if source is None:
            raise KeyError(source_id)
        root = Path(source.root_path)
        if source.subpath:
            root = root.joinpath(*PurePosixPath(source.subpath).parts)
        pending = [
            PendingFile(
                id=entry.id,
                relative_path=entry.relative_path,
                file_size=entry.file_size,
                modified_at=entry.modified_at,
            )
            for entry in session.scalars(
                select(KnowledgeSourceEntry)
                .where(
                    KnowledgeSourceEntry.source_id == source_id,
                    KnowledgeSourceEntry.present.is_(True),
                    KnowledgeSourceEntry.entry_kind == "file",
                    KnowledgeSourceEntry.raw_content_hash.is_(None),
                    KnowledgeSourceEntry.file_size.is_not(None),
                    KnowledgeSourceEntry.modified_at.is_not(None),
                )
                .order_by(KnowledgeSourceEntry.relative_path)
            )
        ]

    summary = {
        "pending": len(pending),
        "processed": 0,
        "hashed": 0,
        "source_changed": 0,
        "read_failed": 0,
        "unsafe_path": 0,
    }

    def persist(results: list[HashResult]) -> None:
        with database.session_factory() as session:
            for result in results:
                summary["processed"] += 1
                summary[result.status] += 1
                if result.raw_content_hash is None:
                    continue
                entry = session.get(KnowledgeSourceEntry, result.item.id)
                if (
                    entry is not None
                    and entry.raw_content_hash is None
                    and entry.file_size == result.item.file_size
                    and entry.modified_at == result.item.modified_at
                ):
                    entry.raw_content_hash = result.raw_content_hash
                else:
                    summary["hashed"] -= 1
                    summary["source_changed"] += 1
            session.commit()
        if progress is not None:
            progress(dict(summary))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        iterator = iter(pending)
        active: set[Future[HashResult]] = set()
        for _ in range(min(len(pending), workers * 4)):
            active.add(executor.submit(_hash_file, root, next(iterator)))
        completed_batch: list[HashResult] = []
        while active:
            completed, active = wait(active, return_when=FIRST_COMPLETED)
            for future in completed:
                completed_batch.append(future.result())
                next_item = next(iterator, None)
                if next_item is not None:
                    active.add(executor.submit(_hash_file, root, next_item))
            if len(completed_batch) >= batch_size:
                persist(completed_batch)
                completed_batch = []
        if completed_batch:
            persist(completed_batch)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill physical file SHA256 provenance for a source."
    )
    parser.add_argument("source_id")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()
    database = Database(get_settings().database_url)
    try:
        result = backfill_raw_content_hashes(
            database,
            args.source_id,
            workers=args.workers,
            batch_size=args.batch_size,
            progress=lambda item: print(
                json.dumps(item, ensure_ascii=False), flush=True
            ),
        )
        print(json.dumps(result, ensure_ascii=False))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
