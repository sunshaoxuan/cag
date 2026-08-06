import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.knowledge.ocr import OcrUnavailableError, TesseractOcrEngine
from app.policies.command_policy import CommandPolicyService


class FakeImage:
    def save(self, stream, *, format: str, dpi: tuple[int, int]) -> None:
        assert format == "PNG"
        assert dpi == (300, 300)
        stream.write(b"png")


class FakeBitmap:
    def to_pil(self) -> FakeImage:
        return FakeImage()

    def close(self) -> None:
        return None


class FakePage:
    def render(self, *, scale: float) -> FakeBitmap:
        assert scale == pytest.approx(300 / 72)
        return FakeBitmap()

    def close(self) -> None:
        return None


class FakeDocument:
    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int) -> FakePage:
        assert index in {0, 1}
        return FakePage()

    def close(self) -> None:
        return None


def test_tesseract_ocr_renders_pages_and_records_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"fixture")
    monkeypatch.setitem(
        sys.modules,
        "pypdfium2",
        SimpleNamespace(PdfDocument=lambda _path: FakeDocument()),
    )

    def fake_run(args, **options):
        assert options["check"] is True
        assert options["capture_output"] is True
        if "--version" in args:
            return subprocess.CompletedProcess(args, 0, b"tesseract 5.4\n", b"")
        assert options["input"] == b"png"
        return subprocess.CompletedProcess(args, 0, b"\xe6\xbb\x8b\xe8\xb3\x80\xe5\xa4\xa7\xe5\xad\xa6", b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    engine = TesseractOcrEngine(
        executable=str(executable),
        languages="jpn+eng",
        dpi=300,
        page_timeout_seconds=30,
        command_policy=CommandPolicyService(),
    )

    result = engine.extract_pdf(tmp_path / "scan.pdf")

    assert result.engine == "tesseract"
    assert result.engine_version == "tesseract 5.4"
    assert result.languages == "jpn+eng"
    assert result.pages == 2
    assert result.text.count("[OCR page ") == 2
    assert "滋賀大学" in result.text
    assert engine.status()["available"] is True


def test_tesseract_ocr_reports_missing_executable(tmp_path: Path) -> None:
    engine = TesseractOcrEngine(
        executable=str(tmp_path / "missing.exe"),
        languages="jpn+eng",
        dpi=300,
        page_timeout_seconds=30,
        command_policy=CommandPolicyService(),
    )

    assert engine.status()["available"] is False
    with pytest.raises(OcrUnavailableError):
        engine.extract_pdf(tmp_path / "scan.pdf")
