from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytesseract
from PIL import Image
from pytesseract import Output


MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

OCR_MONTH_ALIASES = {
    "jui": "jul",
    "jul": "jul",
    "juiy": "jul",
    "july": "jul",
    "lul": "jul",
    "sul": "jul",
}


@dataclass(frozen=True)
class ParsedNumber:
    value: float
    text: str


def extract_lme_market_card(data: bytes, *, source_filename: str | None = None) -> dict:
    image = Image.open(io.BytesIO(data)).convert("RGB")
    width, height = image.size
    raw_text, confidence = _ocr_image(image)
    fields = parse_market_card_text(raw_text)

    warnings = _build_warnings(fields)
    return {
        "template": "lme_market_card_v1",
        "engine": "tesseract-local",
        "sourceFilename": source_filename,
        "imageSha256": hashlib.sha256(data).hexdigest(),
        "image": {
            "width": width,
            "height": height,
            "bytes": len(data),
        },
        "name": fields["name"],
        "nameNormalized": normalize_name(fields["name"]),
        "specification": fields.get("specification") or "",
        "price": fields["price"],
        "priceText": fields["price_text"],
        "currency": fields["currency"],
        "unit": fields["unit"],
        "date": fields["date"],
        "dateText": fields["date_text"],
        "changeValue": fields.get("change_value"),
        "changePercent": fields.get("change_percent"),
        "high": fields.get("high"),
        "low": fields.get("low"),
        "confidence": confidence,
        "requiresReview": bool(warnings),
        "warnings": warnings,
        "rawText": raw_text,
    }


def parse_market_card_text(raw_text: str) -> dict:
    text = _clean_text(raw_text)
    lines = _meaningful_lines(text)
    if not lines:
        raise ValueError("No se pudo leer texto en la imagen.")

    specification_index = _find_line_index(lines, r"\bspecification\b")
    name = _extract_name(lines, specification_index)
    specification = lines[specification_index] if specification_index is not None else ""

    price_match = re.search(
        r"(?P<price>[0-9][0-9\s.,]*?)\s*(?P<currency>USD)\s*/?\s*(?P<unit>kg)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not price_match:
        raise ValueError("No se encontro precio USD/kg.")

    price = _parse_number(price_match.group("price"))
    date_text, date_value = _extract_date(text)
    change_value, change_percent = _extract_change(text)
    high = _extract_labeled_number(text, "High")
    low = _extract_labeled_number(text, "Low")

    return {
        "name": name,
        "specification": specification,
        "price": price.value,
        "price_text": price.text,
        "currency": price_match.group("currency").upper(),
        "unit": price_match.group("unit").lower(),
        "date": date_value,
        "date_text": date_text,
        "change_value": change_value,
        "change_percent": change_percent,
        "high": high,
        "low": low,
    }


def normalize_name(value: str) -> str:
    normalized = _clean_text(value).upper()
    normalized = normalized.replace("1 #", "1#")
    normalized = re.sub(r"[^A-Z0-9#]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _ocr_image(image: Image.Image) -> tuple[str, float | None]:
    config = "--oem 3 --psm 6"
    text = pytesseract.image_to_string(image, lang="eng", config=config)
    data = pytesseract.image_to_data(image, lang="eng", config=config, output_type=Output.DICT)
    return _clean_text(text), _mean_confidence(data)


def _clean_text(value: str) -> str:
    value = value.replace("\x0c", " ")
    value = value.replace("|", " ")
    value = value.replace("]J", " ")
    value = value.replace("] ", " ")
    return re.sub(r"[ \t]+", " ", value).strip()


def _meaningful_lines(text: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if re.sub(r"\s+", " ", line).strip()
    ]


def _find_line_index(lines: list[str], pattern: str) -> int | None:
    for index, line in enumerate(lines):
        if re.search(pattern, line, flags=re.IGNORECASE):
            return index
    return None


def _extract_name(lines: list[str], specification_index: int | None) -> str:
    candidates = lines[:specification_index] if specification_index is not None else lines[:1]
    candidates = [_clean_product_name_line(line) for line in candidates]
    candidates = [line for line in candidates if line]
    if not candidates:
        raise ValueError("No se encontro nombre del producto.")
    return " ".join(candidates).strip()


def _clean_product_name_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line).strip(" =:-")
    if not line:
        return ""
    if re.search(r"\bUSD\s*/?\s*kg\b|\bHigh\b|\bLow\b", line, flags=re.IGNORECASE):
        return ""
    line = re.sub(r"^\s*SMM(?:[-\s]*[A-Z0-9]+){2,}\s*=?\s*", "", line, flags=re.IGNORECASE).strip()
    if not line:
        return ""
    if re.fullmatch(r"SMM(?:[-\s]*[A-Z0-9]+){2,}", line, flags=re.IGNORECASE):
        return ""
    if not re.search(r"[A-Za-z]", line):
        return ""
    return line.strip(" =:-")


def _parse_number(value: str) -> ParsedNumber:
    original = re.sub(r"\s+", " ", value).strip()
    compact = re.sub(r"\s+", "", original)
    compact = compact.replace(",", "")
    if not re.search(r"\d", compact):
        raise ValueError(f"Numero invalido: {original}")
    return ParsedNumber(value=float(compact), text=original)


def _extract_date(text: str) -> tuple[str, str]:
    for match in re.finditer(
        r"\b(?P<month>[A-Za-z]{3,9})\s+(?P<day>[0-9]{1,2}),\s*(?P<year>[0-9]{4})\b",
        text,
        flags=re.IGNORECASE,
    ):
        month_key = re.sub(r"[^a-z]", "", match.group("month").lower())
        month_key = OCR_MONTH_ALIASES.get(month_key, month_key[:3])
        if month_key not in MONTHS:
            continue
        month = MONTHS[month_key]
        parsed = datetime(int(match.group("year")), month, int(match.group("day"))).date()
        return match.group(0), parsed.isoformat()

    raise ValueError("No se encontro fecha.")


def _extract_change(text: str) -> tuple[float | None, float | None]:
    match = re.search(
        r"(?P<value>[+-]?[0-9]+(?:\.[0-9]+)?)\s*\(\s*(?P<percent>[+-]?[0-9]+(?:\.[0-9]+)?)\s*%\s*\)",
        text,
    )
    if not match:
        return None, None
    return float(match.group("value")), float(match.group("percent"))


def _extract_labeled_number(text: str, label: str) -> float | None:
    match = re.search(
        rf"\b{re.escape(label)}\s+(?P<number>[0-9][0-9\s.,]*)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return _parse_number(match.group("number")).value


def _mean_confidence(data: dict[str, list[Any]]) -> float | None:
    values: list[float] = []
    for raw_conf, raw_text in zip(data.get("conf", []), data.get("text", [])):
        if not str(raw_text).strip():
            continue
        try:
            conf = float(raw_conf)
        except (TypeError, ValueError):
            continue
        if conf >= 0:
            values.append(conf)
    return round(sum(values) / len(values), 2) if values else None


def _build_warnings(fields: dict) -> list[str]:
    warnings: list[str] = []
    price = fields.get("price")
    high = fields.get("high")
    low = fields.get("low")

    if not fields.get("name"):
        warnings.append("missing_name")
    if not fields.get("date"):
        warnings.append("missing_date")
    if price is None:
        warnings.append("missing_price")
    if high is None:
        warnings.append("missing_high")
    if low is None:
        warnings.append("missing_low")
    if high is not None and low is not None and high < low:
        warnings.append("invalid_high_low_range")
    if price is not None and high is not None and price > high:
        warnings.append("price_above_high")
    if price is not None and low is not None and price < low:
        warnings.append("price_below_low")

    return warnings
