from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.lme_market_card_parser import extract_lme_market_card
from app.services.tesseract_setup import configure_tesseract


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/extract_folder.py <carpeta>")
        return 2

    configure_tesseract()
    folder = Path(sys.argv[1])
    items = []
    errors = []
    for path in sorted(folder.glob("*")):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        try:
            items.append(extract_lme_market_card(path.read_bytes(), source_filename=path.name))
        except Exception as exc:
            errors.append({"filename": path.name, "message": str(exc)})

    print(json.dumps({"count": len(items), "items": items, "errors": errors}, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
