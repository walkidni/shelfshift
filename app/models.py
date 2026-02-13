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
class Variant:
    id: str | None = None
    sku: str | None = None
    title: str | None = None
    options: dict[str, str] = field(default_factory=dict)  # e.g. {"Color": "Black", "Size": "M"}
    price_amount: float | None = None
    currency: str | None = None
    image: str | None = None
    available: bool | None = None
    inventory_quantity: int | None = None
    weight: float | None = None  # For shipping calculations
    raw: dict[str, Any] | None = None

    def to_dict(self, include_raw: bool = True) -> dict[str, Any]:
        data = {
            "id": self.id,
            "sku": self.sku,
            "title": self.title,
            "options": self.options or {},
            "price_amount": self.price_amount,
            "currency": self.currency,
            "image": self.image,
            "available": self.available,
            "inventory_quantity": self.inventory_quantity,
            "weight": self.weight,
        }
        if include_raw:
            data["raw"] = self.raw
        return data


@dataclass
class ProductResult:
    platform: str
    id: str | None
    title: str | None
    description: str | None
    price: dict[str, Any] | None  # {"amount": float|None, "currency": str|None} (typically min/current)
    images: list[str] = field(default_factory=list)
    raw: dict[str, Any] | None = None
    options: dict[str, list[str]] = field(default_factory=dict)  # {"Color": ["Black","White"], "Size": ["S","M"]}
    variants: list[Variant] = field(default_factory=list)
    brand: str | None = None  # Product brand for metadata
    category: str | None = None  # Product category for SEO and organization
    meta_title: str | None = None  # Custom page title for SEO
    meta_description: str | None = None  # Custom meta description for SEO
    slug: str | None = None  # Source URL slug if available
    tags: list[str] = field(default_factory=list)  # Tags for searchability
    vendor: str | None = None  # Vendor/supplier name
    weight: float | None = None  # Default product weight
    requires_shipping: bool = True  # Whether product needs shipping
    track_quantity: bool = True  # Whether to track inventory
    is_digital: bool = False  # Digital product flag

    def to_dict(self, include_raw: bool = True) -> dict[str, Any]:
        data = {
            "platform": self.platform,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "images": self.images,
            "options": self.options,
            "variants": [v.to_dict(include_raw=include_raw) for v in self.variants],
            "brand": self.brand,
            "category": self.category,
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "slug": self.slug,
            "tags": self.tags,
            "vendor": self.vendor,
            "weight": self.weight,
            "requires_shipping": self.requires_shipping,
            "track_quantity": self.track_quantity,
            "is_digital": self.is_digital,
        }
        if include_raw:
            data["raw"] = self.raw
        return data


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
    "ProductResult",
    "Variant",
    "Weight",
    "WeightUnit",
    "format_decimal",
    "normalize_currency",
    "parse_decimal_money",
]
