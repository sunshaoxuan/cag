from __future__ import annotations

import io
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.policies.command_policy import CommandPolicyService


class OcrUnavailableError(RuntimeError):
    reason_code = "ocr_unavailable"


@dataclass(frozen=True)
class OcrResult:
    text: str
    engine: str
    engine_version: str
    languages: str
    pages: int


class TesseractOcrEngine:
    def __init__(
        self,
        *,
        executable: str,
        languages: str,
        dpi: int,
        page_timeout_seconds: int,
        command_policy: CommandPolicyService,
    ) -> None:
        self._executable = executable
        self._languages = languages
        self._dpi = dpi
        self._page_timeout_seconds = page_timeout_seconds
        self._policy = command_policy

    @property
    def available(self) -> bool:
        return bool(shutil.which(self._executable) or Path(self._executable).is_file())

    def status(self) -> dict[str, str | bool]:
        if not self.available:
            return {
                "available": False,
                "engine": "tesseract",
                "languages": self._languages,
            }
        return {
            "available": True,
            "engine": "tesseract",
            "version": self._version(),
            "languages": self._languages,
        }

    def extract_pdf(self, path: Path) -> OcrResult:
        if not self.available:
            raise OcrUnavailableError("Tesseract OCR executable is unavailable")
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise OcrUnavailableError(
                "PDF OCR requires the pypdfium2 package"
            ) from exc
        document = pdfium.PdfDocument(str(path))
        page_text: list[str] = []
        try:
            for index in range(len(document)):
                page = document[index]
                bitmap = page.render(scale=self._dpi / 72)
                image = bitmap.to_pil()
                payload = io.BytesIO()
                image.save(payload, format="PNG", dpi=(self._dpi, self._dpi))
                completed = self._run(
                    [
                        self._executable,
                        "stdin",
                        "stdout",
                        "-l",
                        self._languages,
                        "--dpi",
                        str(self._dpi),
                    ],
                    input_bytes=payload.getvalue(),
                )
                recognized = completed.stdout.decode(
                    "utf-8",
                    errors="replace",
                ).strip()
                page_text.append(
                    f"[OCR page {index + 1}]\n{recognized}"
                )
                bitmap.close()
                page.close()
        finally:
            document.close()
        return OcrResult(
            text="\n\n".join(page_text),
            engine="tesseract",
            engine_version=self._version(),
            languages=self._languages,
            pages=len(page_text),
        )

    def _version(self) -> str:
        completed = self._run([self._executable, "--version"])
        return completed.stdout.decode(
            "utf-8",
            errors="replace",
        ).splitlines()[0][:64]

    def _run(
        self,
        args: list[str],
        *,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        decision = self._policy.evaluate("tesseract ocr", "knowledge_collection")
        if decision.decision != "allow":
            raise PermissionError(decision.reason)
        try:
            return subprocess.run(
                args,
                check=True,
                capture_output=True,
                input=input_bytes,
                timeout=self._page_timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise OcrUnavailableError(
                "Tesseract OCR executable is unavailable"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Tesseract OCR page timeout") from exc
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(message[:500] or "Tesseract OCR failed") from exc
