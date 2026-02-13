from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any

_MONEY_SANITIZE_RE = re.compile(r"[^\d\.\-]")


def parse_decimal_money(value: Any) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value if value.is_finite() else None

    if isinstance(value, int):
        return Decimal(str(value))

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        try:
            parsed = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        return parsed if parsed.is_finite() else None

    if isinstance(value, str):
        cleaned = _MONEY_SANITIZE_RE.sub("", value.strip().replace(",", ""))
        if cleaned in {"", "-", ".", "-."}:
            return None
        try:
            parsed = Decimal(cleaned)
        except InvalidOperation:
            return None
        return parsed if parsed.is_finite() else None

    return None


def normalize_currency(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    return normalized or None


def format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    if not value.is_finite():
        return ""

    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


__all__ = [
    "format_decimal",
    "normalize_currency",
    "parse_decimal_money",
]
