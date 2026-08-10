from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.knowledge.code_intelligence import CODE_LANGUAGE_BY_SUFFIX
from app.knowledge.extractors import SUPPORTED_EXTENSIONS


PROCESSING_POLICY_VERSION = "knowledge-routing-v5"
CODE_PROCESSOR_VERSION = "structural-code-v4-subpath-embedding"
DOCUMENT_PROCESSOR_VERSION = "document-text-v5-structured-location"
PATH_PROCESSOR_VERSION = "path-semantic-v3-subpath-embedding"

METADATA_ONLY_EXTENSIONS = {
    ".7z",
    ".bak",
    ".backup",
    ".bin",
    ".bkp",
    ".bz2",
    ".dmp",
    ".dump",
    ".ear",
    ".gz",
    ".img",
    ".iso",
    ".jar",
    ".rar",
    ".tar",
    ".tgz",
    ".vhd",
    ".vhdx",
    ".war",
    ".xz",
    ".zip",
}
_DUMP_NAME_PATTERN = re.compile(
    r"(^|[._-])(backup|database[-_]?dump|db[-_]?dump|dump|export)"
    r"([._-]|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FileProcessingDecision:
    mode: str
    reason_code: str | None


def classify_file(
    relative_path: str,
    *,
    file_size: int,
    max_file_bytes: int,
) -> FileProcessingDecision:
    path = PurePosixPath(relative_path)
    suffix = path.suffix.lower()
    if path.name.startswith("~$") and suffix in {
        ".docx",
        ".pptx",
        ".xlsx",
        ".xlsm",
    }:
        return FileProcessingDecision(
            "metadata_only",
            "temporary_office_file",
        )
    if suffix == ".lnk":
        return FileProcessingDecision("path_only", "windows_shortcut")
    if suffix in METADATA_ONLY_EXTENSIONS:
        return FileProcessingDecision(
            "metadata_only",
            "metadata_only_policy",
        )
    if file_size > max_file_bytes:
        return FileProcessingDecision("metadata_only", "file_too_large")
    if suffix == ".sql" and _DUMP_NAME_PATTERN.search(path.name):
        return FileProcessingDecision(
            "metadata_only",
            "database_dump_policy",
        )
    if file_size == 0:
        return FileProcessingDecision("path_only", "empty_file_path_only")
    if suffix in CODE_LANGUAGE_BY_SUFFIX:
        return FileProcessingDecision("code", None)
    if suffix in SUPPORTED_EXTENSIONS:
        return FileProcessingDecision("document", None)
    return FileProcessingDecision(
        "metadata_only",
        "unsupported_extension",
    )


def processor_fingerprint(
    processing_mode: str,
    *,
    embedding_model: str,
    embedding_dimensions: int,
    processor_variant: str | None = None,
) -> str:
    processor_version = {
        "code": CODE_PROCESSOR_VERSION,
        "document": DOCUMENT_PROCESSOR_VERSION,
        "path_only": PATH_PROCESSOR_VERSION,
    }.get(processing_mode, PROCESSING_POLICY_VERSION)
    payload = {
        "policy": PROCESSING_POLICY_VERSION,
        "mode": processing_mode,
        "processor": processor_version,
        "embedding_model": embedding_model,
        "embedding_dimensions": embedding_dimensions,
    }
    if processor_variant is not None:
        payload["variant"] = processor_variant
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def path_semantic_text(relative_path: str, *, reason_code: str) -> str:
    path = PurePosixPath(relative_path)
    parent_parts = [part for part in path.parent.parts if part not in {".", ""}]
    return "\n".join(
        (
            f"relative_path: {relative_path}",
            f"file_name: {path.name}",
            f"file_stem: {path.stem}",
            f"extension: {path.suffix.lower()}",
            f"directories: {' / '.join(parent_parts)}",
            f"entry_state: {reason_code}",
        )
    )
