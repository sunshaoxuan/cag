from __future__ import annotations

import email
import importlib.metadata
import io
import multiprocessing
import os
import shutil
import socket
import stat
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from email import policy
from pathlib import Path, PurePosixPath
from typing import Callable

from app.knowledge.content_probe import ContentProbeResult, probe_content


FRAMEWORK_VERSION = "safe-extraction-v1"


class StableExtractionError(RuntimeError):
    def __init__(
        self,
        reason_code: str,
        message: str,
        *,
        retryable: bool = False,
        processor: str = "safe-extraction-worker",
        processor_version: str = FRAMEWORK_VERSION,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.retryable = retryable
        self.processor = processor
        self.processor_version = processor_version


@dataclass(frozen=True)
class ExtractionLimits:
    timeout_seconds: int = 120
    max_input_bytes: int = 100_000_000
    max_output_characters: int = 10_000_000
    max_archive_members: int = 2_000
    max_archive_uncompressed_bytes: int = 250_000_000
    max_archive_compression_ratio: int = 200
    max_spreadsheet_cells: int = 250_000


@dataclass(frozen=True)
class ExtractorCapability:
    name: str
    version: str
    magic_types: tuple[str, ...]


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    encoding: str
    processor: str
    processor_version: str
    processor_variant: str
    probe: ContentProbeResult


Extractor = Callable[[Path, ContentProbeResult, ExtractionLimits], tuple[str, str]]


class ExtractorRegistry:
    def __init__(self) -> None:
        self._items: list[tuple[ExtractorCapability, Extractor]] = []

    def register(self, capability: ExtractorCapability, extractor: Extractor) -> None:
        if any(existing.name == capability.name for existing, _ in self._items):
            raise ValueError(f"Duplicate extractor: {capability.name}")
        self._items.append((capability, extractor))

    def resolve(self, probe: ContentProbeResult) -> tuple[ExtractorCapability, Extractor]:
        for capability, extractor in self._items:
            if probe.magic_type in capability.magic_types:
                return capability, extractor
        if probe.is_probably_text:
            for capability, extractor in self._items:
                if "plain_text" in capability.magic_types:
                    return capability, extractor
        raise StableExtractionError(
            "binary_content_not_extractable",
            "Content probe classified the file as non-text binary data",
        )


def default_registry() -> ExtractorRegistry:
    registry = ExtractorRegistry()
    registry.register(ExtractorCapability("plain-text", FRAMEWORK_VERSION, ("plain_text",)), _extract_plain_text)
    registry.register(ExtractorCapability("rtf", _version("striprtf"), ("rtf",)), _extract_rtf)
    registry.register(ExtractorCapability("rfc822", FRAMEWORK_VERSION, ("rfc822",)), _extract_email)
    registry.register(ExtractorCapability("ole-compound", _version("olefile"), ("ole_compound",)), _extract_ole)
    registry.register(ExtractorCapability("safe-zip", FRAMEWORK_VERSION, ("zip",)), _extract_archive)
    return registry


def extract_isolated(path: Path, limits: ExtractionLimits) -> ExtractionResult:
    if path.stat().st_size > limits.max_input_bytes:
        raise StableExtractionError("input_size_limit_exceeded", "Input exceeds configured byte limit")
    with tempfile.TemporaryDirectory(prefix="cag-extract-") as temporary:
        staged = Path(temporary) / f"input{path.suffix.lower()}"
        shutil.copyfile(path, staged)
        staged.chmod(stat.S_IREAD)
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=False)
        process = context.Process(target=_worker_entry, args=(str(staged), asdict(limits), child), daemon=True)
        process.start()
        child.close()
        try:
            if not parent.poll(limits.timeout_seconds):
                process.terminate()
                process.join(5)
                raise StableExtractionError("extraction_timeout", "Extraction worker exceeded its time limit", retryable=True)
            payload = parent.recv()
        finally:
            parent.close()
            if process.is_alive():
                process.terminate()
            process.join(5)
            staged.chmod(stat.S_IWRITE)
    if not payload["ok"]:
        raise StableExtractionError(**payload["error"])
    result = payload["result"]
    return ExtractionResult(probe=ContentProbeResult(**result.pop("probe")), **result)


def _worker_entry(path: str, limits: dict[str, int], connection) -> None:
    try:
        _disable_network()
        selected_limits = ExtractionLimits(**limits)
        target = Path(path)
        probe = probe_content(target)
        capability, extractor = default_registry().resolve(probe)
        text, encoding = extractor(target, probe, selected_limits)
        if len(text) > selected_limits.max_output_characters:
            raise StableExtractionError("output_size_limit_exceeded", "Extracted text exceeds configured limit")
        connection.send({"ok": True, "result": {
            "text": text,
            "encoding": encoding,
            "processor": capability.name,
            "processor_version": capability.version,
            "processor_variant": f"{FRAMEWORK_VERSION}:{probe.magic_type}",
            "probe": asdict(probe),
        }})
    except StableExtractionError as exc:
        connection.send({"ok": False, "error": {
            "reason_code": exc.reason_code,
            "message": str(exc),
            "retryable": exc.retryable,
            "processor": exc.processor,
            "processor_version": exc.processor_version,
        }})
    except Exception as exc:
        connection.send({"ok": False, "error": {
            "reason_code": "extractor_rejected",
            "message": type(exc).__name__,
            "retryable": False,
            "processor": "safe-extraction-worker",
            "processor_version": FRAMEWORK_VERSION,
        }})
    finally:
        connection.close()


def _disable_network() -> None:
    def blocked(*_args, **_kwargs):
        raise PermissionError("Network access is disabled in extraction workers")
    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]


def _extract_plain_text(path: Path, _probe: ContentProbeResult, _limits: ExtractionLimits) -> tuple[str, str]:
    from app.knowledge.extractors import detect_text_encoding
    raw = path.read_bytes()
    encoding = detect_text_encoding(raw)
    return raw.decode(encoding), encoding


def _extract_rtf(path: Path, _probe: ContentProbeResult, _limits: ExtractionLimits) -> tuple[str, str]:
    from striprtf.striprtf import rtf_to_text
    raw = path.read_bytes()
    return rtf_to_text(raw.decode("latin-1"), errors="strict"), "rtf"


def _extract_email(path: Path, _probe: ContentProbeResult, limits: ExtractionLimits) -> tuple[str, str]:
    message = email.message_from_bytes(path.read_bytes(), policy=policy.default)
    lines = [f"Subject: {message.get('subject', '')}", f"From: {message.get('from', '')}", f"To: {message.get('to', '')}", f"Date: {message.get('date', '')}"]
    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            lines.append(f"[attachment] {part.get_filename() or 'unnamed'} {part.get_content_type()}")
            continue
        if part.get_content_type() == "text/plain":
            content = part.get_content()
            if isinstance(content, str):
                lines.append(content)
        if sum(map(len, lines)) > limits.max_output_characters:
            raise StableExtractionError("output_size_limit_exceeded", "Email text exceeds configured limit")
    return "\n".join(lines), "rfc822"


def _extract_ole(path: Path, _probe: ContentProbeResult, limits: ExtractionLimits) -> tuple[str, str]:
    if path.suffix.lower() == ".xls":
        return _extract_legacy_xls(path, limits)
    if path.suffix.lower() == ".msg":
        return _extract_outlook_msg(path, limits)
    import olefile
    parts: list[str] = []
    total = 0
    with olefile.OleFileIO(path) as container:
        for stream_name in container.listdir(streams=True, storages=False):
            name = "/".join(stream_name)
            raw = container.openstream(stream_name).read(min(limits.max_output_characters * 2, limits.max_archive_uncompressed_bytes))
            candidates = _printable_runs(raw.decode("utf-16-le", errors="ignore")) + _printable_runs(raw.decode("cp932", errors="ignore"))
            if candidates:
                value = f"[stream] {name}\n" + "\n".join(candidates)
                total += len(value)
                if total > limits.max_output_characters:
                    raise StableExtractionError("output_size_limit_exceeded", "OLE text exceeds configured limit")
                parts.append(value)
    if not parts:
        raise StableExtractionError("ole_text_not_found", "OLE container contains no safely extractable text")
    return "\n".join(parts), "ole-streams"


def _extract_legacy_xls(path: Path, limits: ExtractionLimits) -> tuple[str, str]:
    import xlrd
    workbook = xlrd.open_workbook(path, on_demand=True)
    lines: list[str] = []
    cells = 0
    try:
        for index, sheet in enumerate(workbook.sheets(), start=1):
            lines.append(f"[sheet] index={index} name={sheet.name}")
            for row in range(sheet.nrows):
                for column in range(sheet.ncols):
                    value = sheet.cell_value(row, column)
                    if value in (None, ""):
                        continue
                    cells += 1
                    if cells > limits.max_spreadsheet_cells:
                        raise StableExtractionError("spreadsheet_cell_limit_exceeded", "Legacy spreadsheet cell count exceeds configured limit")
                    lines.append(f"R{row + 1}C{column + 1}\tvalue={value}")
                    if sum(map(len, lines)) > limits.max_output_characters:
                        raise StableExtractionError("output_size_limit_exceeded", "Legacy spreadsheet text exceeds configured limit")
    finally:
        workbook.release_resources()
    return "\n".join(lines), "xls-semantic"


def _extract_outlook_msg(path: Path, limits: ExtractionLimits) -> tuple[str, str]:
    import extract_msg
    message = extract_msg.Message(path)
    try:
        attachments = [
            f"[attachment] {getattr(item, 'longFilename', None) or getattr(item, 'shortFilename', None) or 'unnamed'}"
            for item in message.attachments
        ]
        text = "\n".join(
            [
                f"Subject: {message.subject or ''}",
                f"From: {message.sender or ''}",
                f"To: {message.to or ''}",
                f"Date: {message.date or ''}",
                message.body or "",
                *attachments,
            ]
        )
        if len(text) > limits.max_output_characters:
            raise StableExtractionError("output_size_limit_exceeded", "Outlook message text exceeds configured limit")
        return text, "outlook-msg"
    finally:
        message.close()


def _printable_runs(text: str) -> list[str]:
    runs: list[str] = []
    current: list[str] = []
    for character in text:
        if character.isprintable() or character in "\t":
            current.append(character)
        else:
            if len(current) >= 4:
                runs.append("".join(current).strip())
            current = []
    if len(current) >= 4:
        runs.append("".join(current).strip())
    return [value for value in runs if value]


def _extract_archive(path: Path, _probe: ContentProbeResult, limits: ExtractionLimits) -> tuple[str, str]:
    output: list[str] = []
    output_size = 0
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > limits.max_archive_members:
            raise StableExtractionError("archive_member_limit_exceeded", "Archive member count exceeds configured limit")
        expanded = sum(item.file_size for item in members)
        if expanded > limits.max_archive_uncompressed_bytes:
            raise StableExtractionError("archive_expanded_size_limit_exceeded", "Archive expanded size exceeds configured limit")
        for item in members:
            normalized = PurePosixPath(item.filename.replace("\\", "/"))
            if normalized.is_absolute() or ".." in normalized.parts:
                raise StableExtractionError("archive_path_traversal", "Archive contains an unsafe member path")
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise StableExtractionError("archive_link_rejected", "Archive contains a symbolic link")
            if item.file_size and item.file_size / max(1, item.compress_size) > limits.max_archive_compression_ratio:
                raise StableExtractionError("archive_compression_ratio_exceeded", "Archive member compression ratio exceeds configured limit")
            if item.is_dir():
                continue
            raw = archive.read(item)
            if b"\x00" in raw:
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = raw.decode("cp932")
                except UnicodeDecodeError:
                    continue
            value = f"[archive member] {normalized.as_posix()}\n{text}"
            output_size += len(value)
            if output_size > limits.max_output_characters:
                raise StableExtractionError("output_size_limit_exceeded", "Archive text exceeds configured limit")
            output.append(value)
    if not output:
        raise StableExtractionError("archive_text_not_found", "Archive contains no safely extractable text")
    return "\n".join(output), "archive-members"


def _version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"
