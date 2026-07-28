import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


TEXT_EXTENSIONS = {
    ".c",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".go",
    ".h",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".log",
    ".md",
    ".php",
    ".properties",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".rst",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".odt"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | OFFICE_EXTENSIONS | {".pdf"}


@dataclass(frozen=True)
class ExtractedText:
    text: str
    encoding: str


def extract_text(path: Path) -> str:
    return extract_text_with_metadata(path).text


def extract_text_with_metadata(path: Path) -> ExtractedText:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        raw = path.read_bytes()
        encoding = detect_text_encoding(raw)
        return ExtractedText(raw.decode(encoding), encoding)
    if suffix in OFFICE_EXTENSIONS:
        return ExtractedText(_extract_zipped_xml(path), "office-xml")
    if suffix == ".pdf":
        return ExtractedText(_extract_pdf(path), "pdf-text")
    raise ValueError(f"Unsupported knowledge file type: {suffix}")


def detect_text_encoding(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if raw.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if raw.startswith(b"\xfe\xff"):
        return "utf-16-be"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    for encoding in ("cp932", "shift_jis"):
        try:
            raw.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(
        "supported-enterprise-text",
        raw,
        0,
        min(1, len(raw)),
        "expected UTF-8, UTF-16, CP932, or Shift-JIS",
    )


def _extract_zipped_xml(path: Path) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".xml"):
                continue
            if not (
                name.startswith("word/")
                or name.startswith("ppt/slides/")
                or name.startswith("xl/sharedStrings")
                or name.startswith("xl/worksheets/")
                or name == "content.xml"
            ):
                continue
            root = ElementTree.fromstring(archive.read(name))
            text = " ".join(
                value.strip()
                for value in root.itertext()
                if value and value.strip()
            )
            if text:
                parts.append(text)
    return "\n".join(parts)


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        raise RuntimeError(
            "PDF indexing requires the pypdf package"
        ) from exc
    try:
        reader = PdfReader(str(path))
        return "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except PdfReadError as exc:
        raise ValueError(f"PDF cannot be read: {exc}") from exc


def normalize_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"\r\n?", "\n", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()
