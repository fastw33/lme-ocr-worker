from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _csv_env(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.lower() in {"1", "true", "yes", "si"}


class Settings:
    app_name: str = os.getenv("APP_NAME", "LME OCR Worker")
    app_debug: bool = _bool_env("APP_DEBUG")
    cors_origins: list[str] = _csv_env("CORS_ORIGINS")
    cors_allow_methods: list[str] = _csv_env("CORS_ALLOW_METHODS")
    cors_allow_headers: list[str] = _csv_env("CORS_ALLOW_HEADERS")
    cors_allow_credentials: bool = _bool_env("CORS_ALLOW_CREDENTIALS")
    tesseract_cmd: str = os.getenv("TESSERACT_CMD", "")
    tessdata_prefix: str = os.getenv("TESSDATA_PREFIX", "")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))


@lru_cache
def get_settings() -> Settings:
    return Settings()
