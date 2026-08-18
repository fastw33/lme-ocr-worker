from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    app_name: str = os.getenv("APP_NAME", "LME OCR Worker")
    app_debug: bool = os.getenv("APP_DEBUG", "false").lower() == "true"
    tesseract_cmd: str = os.getenv("TESSERACT_CMD", "")
    tessdata_prefix: str = os.getenv("TESSDATA_PREFIX", "")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))


@lru_cache
def get_settings() -> Settings:
    return Settings()
