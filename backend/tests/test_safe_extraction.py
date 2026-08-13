from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from PIL import Image

from app.knowledge.content_probe import probe_content
from app.knowledge.extraction_framework import (
    ExtractionLimits,
    StableExtractionError,
    extract_isolated,
)


def test_unknown_extension_text_is_detected_and_extracted(tmp_path: Path) -> None:
    source = tmp_path / "svn.connection"
    source.write_text("滋賀大学 SVN remote connection", encoding="utf-8")

    probe = probe_content(source)
    result = extract_isolated(source, ExtractionLimits(timeout_seconds=10))

    assert probe.magic_type == "plain_text"
    assert probe.text_probability == 1.0
    assert probe.mime_type == "text/plain"
    assert result.processor == "plain-text"
    assert "SVN remote connection" in result.text
    assert source.read_text(encoding="utf-8") == "滋賀大学 SVN remote connection"


def test_binary_content_is_stably_rejected(tmp_path: Path) -> None:
    source = tmp_path / "payload.txt"
    source.write_bytes(b"MZ\x00\x01\x02\x03")

    with pytest.raises(StableExtractionError) as raised:
        extract_isolated(source, ExtractionLimits(timeout_seconds=10))

    assert raised.value.reason_code == "binary_content_not_extractable"
    assert raised.value.retryable is False
    assert raised.value.processor_version


def test_rtf_and_email_are_extracted(tmp_path: Path) -> None:
    rtf = tmp_path / "guide.rtf"
    rtf.write_text(r"{\rtf1\ansi SVN connection guide}", encoding="ascii")
    eml = tmp_path / "notice.eml"
    eml.write_text(
        "From: admin@example.test\nTo: user@example.test\n"
        "Subject: SVN notice\nMessage-ID: <1@example.test>\n"
        "Content-Type: text/plain; charset=utf-8\n\n接続手順",
        encoding="utf-8",
    )

    rtf_result = extract_isolated(rtf, ExtractionLimits(timeout_seconds=10))
    email_result = extract_isolated(eml, ExtractionLimits(timeout_seconds=10))

    assert rtf_result.processor == "rtf"
    assert "SVN connection guide" in rtf_result.text
    assert email_result.processor == "rfc822"
    assert "接続手順" in email_result.text


def test_safe_archive_extracts_text_members(tmp_path: Path) -> None:
    archive = tmp_path / "evidence.zip"
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr("docs/svn.txt", "SVN 接続資料")
        writer.writestr("bin/payload.bin", b"\x00\x01\x02")

    result = extract_isolated(archive, ExtractionLimits(timeout_seconds=10))

    assert result.processor == "safe-zip"
    assert "docs/svn.txt" in result.text
    assert "SVN 接続資料" in result.text


def test_archive_path_traversal_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "traversal.zip"
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr("../escape.txt", "blocked")

    with pytest.raises(StableExtractionError) as raised:
        extract_isolated(archive, ExtractionLimits(timeout_seconds=10))

    assert raised.value.reason_code == "archive_path_traversal"


def test_archive_bomb_limits_are_stable(tmp_path: Path) -> None:
    archive = tmp_path / "bomb.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as writer:
        writer.writestr("large.txt", "A" * 100_000)

    with pytest.raises(StableExtractionError) as raised:
        extract_isolated(
            archive,
            ExtractionLimits(
                timeout_seconds=10,
                max_archive_uncompressed_bytes=1_000,
            ),
        )

    assert raised.value.reason_code == "archive_expanded_size_limit_exceeded"


def test_image_magic_is_detected_independent_of_extension(tmp_path: Path) -> None:
    image = tmp_path / "connection.data"
    Image.new("RGB", (10, 10), color="white").save(image, format="PNG")

    probe = probe_content(image)

    assert probe.magic_type == "image_png"
    assert probe.mime_type == "image/png"
    assert probe.text_probability == 0.0


def test_pdf_ole_and_ooxml_magic_are_detected(tmp_path: Path) -> None:
    pdf = tmp_path / "manual.data"
    pdf.write_bytes(b"%PDF-1.7\n")
    ole = tmp_path / "legacy.data"
    ole.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1") + b"\x00" * 32)
    document = tmp_path / "document.data"
    with zipfile.ZipFile(document, "w") as writer:
        writer.writestr("[Content_Types].xml", "<Types/>")
        writer.writestr("word/document.xml", "<document/>")

    assert probe_content(pdf).magic_type == "pdf"
    assert probe_content(pdf).mime_type == "application/pdf"
    assert probe_content(ole).magic_type == "ole_compound"
    assert probe_content(ole).mime_type == "application/x-ole-storage"
    assert probe_content(document).magic_type == "ooxml_word"


def test_probe_handles_utf16_email_and_invalid_zip(tmp_path: Path) -> None:
    utf16 = tmp_path / "settings.bin"
    utf16.write_bytes(b"\xff\xfe" + "接続設定".encode("utf-16-le"))
    eml = tmp_path / "message.bin"
    eml.write_text(
        "From: a@example.test\nSubject: notice\nMessage-ID: <x>\n\nbody",
        encoding="ascii",
    )
    invalid_zip = tmp_path / "broken.zip"
    invalid_zip.write_bytes(b"PK\x03\x04broken")

    assert probe_content(utf16).text_probability == 1.0
    assert probe_content(eml).magic_type == "rfc822"
    assert probe_content(invalid_zip).magic_type == "zip"
