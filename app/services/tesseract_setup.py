from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytesseract

from app.core.config import PROJECT_ROOT, get_settings


class OCRSetupError(RuntimeError):
    pass


def configure_tesseract() -> str:
    settings = get_settings()
    candidates = [
        settings.tesseract_cmd,
        shutil.which("tesseract") or "",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidate
            tessdata = _resolve_tessdata(settings.tessdata_prefix)
            if tessdata:
                os.environ["TESSDATA_PREFIX"] = str(tessdata)
            return candidate

    raise OCRSetupError("No se encontro Tesseract OCR. Configura TESSERACT_CMD en .env.")


def _resolve_tessdata(value: str) -> Path | None:
    candidates: list[Path] = []
    if value:
        raw = Path(value)
        candidates.append(raw if raw.is_absolute() else (PROJECT_ROOT / raw).resolve())

    candidates.extend(
        [
            (PROJECT_ROOT.parent / "OCR" / "tessdata").resolve(),
            Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
        ]
    )

    for candidate in candidates:
        if (candidate / "eng.traineddata").is_file():
            return candidate
    return None
