from __future__ import annotations

import mimetypes
import zipfile
from dataclasses import dataclass
from pathlib import Path


PROBE_VERSION = "content-probe-v1"
_SAMPLE_BYTES = 65_536


@dataclass(frozen=True)
class ContentProbeResult:
    mime_type: str
    magic_type: str
    text_probability: float
    extension_hint: str

    @property
    def is_probably_text(self) -> bool:
        return self.text_probability >= 0.85


def probe_content(path: Path) -> ContentProbeResult:
    with path.open("rb") as stream:
        sample = stream.read(_SAMPLE_BYTES)
    extension = path.suffix.lower()
    mime_hint = mimetypes.guess_type(path.name, strict=False)[0]
    magic_type, magic_mime = _magic(sample, path)
    probability = _text_probability(sample)
    if magic_type == "plain_text":
        magic_mime = mime_hint if mime_hint and mime_hint.startswith("text/") else "text/plain"
    return ContentProbeResult(
        mime_type=magic_mime or mime_hint or "application/octet-stream",
        magic_type=magic_type,
        text_probability=probability,
        extension_hint=extension,
    )


def _magic(sample: bytes, path: Path) -> tuple[str, str | None]:
    if sample.startswith(b"%PDF-"):
        return "pdf", "application/pdf"
    if sample.startswith(b"{\\rtf"):
        return "rtf", "application/rtf"
    if sample.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return "ole_compound", "application/x-ole-storage"
    if sample.startswith(b"PK\x03\x04"):
        return _zip_kind(path)
    image_signatures = (
        (b"\x89PNG\r\n\x1a\n", "image_png", "image/png"),
        (b"\xff\xd8\xff", "image_jpeg", "image/jpeg"),
        (b"GIF87a", "image_gif", "image/gif"),
        (b"GIF89a", "image_gif", "image/gif"),
        (b"BM", "image_bmp", "image/bmp"),
        (b"II*\x00", "image_tiff", "image/tiff"),
        (b"MM\x00*", "image_tiff", "image/tiff"),
    )
    for signature, name, mime in image_signatures:
        if sample.startswith(signature):
            return name, mime
    if _looks_like_email(sample):
        return "rfc822", "message/rfc822"
    if _text_probability(sample) >= 0.85:
        return "plain_text", "text/plain"
    return "unknown_binary", None


def _zip_kind(path: Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
    except (OSError, zipfile.BadZipFile):
        return "zip", "application/zip"
    if "[Content_Types].xml" in names:
        if any(name.startswith("word/") for name in names):
            return "ooxml_word", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if any(name.startswith("ppt/") for name in names):
            return "ooxml_presentation", "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        if any(name.startswith("xl/") for name in names):
            return "ooxml_spreadsheet", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if "content.xml" in names:
        return "open_document", "application/vnd.oasis.opendocument.text"
    return "zip", "application/zip"


def _text_probability(raw: bytes) -> float:
    if not raw:
        return 1.0
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return 1.0
    if b"\x00" in raw:
        return 0.0
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        for encoding in ("cp932", "shift_jis"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            return 0.0
    acceptable = sum(character.isprintable() or character in "\r\n\t" for character in text)
    return round(acceptable / max(1, len(text)), 4)


def _looks_like_email(raw: bytes) -> bool:
    head = raw[:8192].decode("ascii", errors="ignore").lower()
    return "\nfrom:" in f"\n{head}" and "\nsubject:" in f"\n{head}" and "\nmessage-id:" in f"\n{head}"
