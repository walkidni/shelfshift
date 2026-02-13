from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any, Literal

Currency = str
WeightUnit = Literal["g", "kg", "lb", "oz"]
MediaType = Literal["image", "video"]

_MONEY_SANITIZE_RE = re.compile(r"[^\d\.\-]")


@dataclass
class Money:
    amount: Decimal | None = None
    currency: Currency | None = None


@dataclass
class Price:
    current: Money = field(default_factory=Money)
    compare_at: Money | None = None
    cost: Money | None = None
    min_price: Money | None = None
    max_price: Money | None = None


@dataclass
class Weight:
    value: Decimal | None = None
    unit: WeightUnit = "g"


@dataclass
class Media:
    url: str
    type: MediaType = "image"
    alt: str | None = None
    position: int | None = None
    is_primary: bool | None = None
    variant_skus: list[str] = field(default_factory=list)


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
    "Currency",
    "Media",
    "MediaType",
    "Money",
    "Price",
    "Weight",
    "WeightUnit",
    "format_decimal",
    "normalize_currency",
    "parse_decimal_money",
]
