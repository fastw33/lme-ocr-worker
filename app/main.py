from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.core.auth import auth_http_middleware
from app.core.config import get_settings
from app.services.lme_market_card_parser import extract_lme_market_card
from app.services.tesseract_setup import configure_tesseract


settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.app_debug, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

app.middleware("http")(auth_http_middleware)


@app.on_event("startup")
def startup() -> None:
    configure_tesseract()


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"ok": True, "service": settings.app_name}


@app.post("/extract/lme-market-card", tags=["extract"])
async def extract_market_cards(files: list[UploadFile] = File(...)) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="Debe enviar al menos una imagen.")

    items: list[dict] = []
    errors: list[dict] = []
    for file in files:
        data = await file.read()
        try:
            _validate_upload(file, data)
            item = await run_in_threadpool(
                extract_lme_market_card,
                data,
                source_filename=file.filename,
            )
            items.append(item)
        except ValueError as exc:
            errors.append({"filename": file.filename, "message": str(exc)})
        except Exception as exc:
            errors.append({"filename": file.filename, "message": str(exc) or exc.__class__.__name__})

    return {
        "ok": len(errors) == 0,
        "template": "lme_market_card_v1",
        "count": len(items),
        "items": items,
        "errors": errors,
    }


def _validate_upload(file: UploadFile, data: bytes) -> None:
    if not data:
        raise ValueError("El archivo esta vacio.")
    if len(data) > settings.max_upload_bytes:
        raise ValueError("La imagen supera el tamano maximo permitido.")

    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()
    allowed_extensions = (".jpg", ".jpeg", ".png", ".webp")
    if content_type and not content_type.startswith("image/"):
        raise ValueError("El archivo debe ser una imagen.")
    if filename and not filename.endswith(allowed_extensions):
        raise ValueError("Formato no soportado. Usa JPG, PNG o WebP.")
