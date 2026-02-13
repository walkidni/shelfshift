from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

Currency = str
WeightUnit = Literal["g", "kg", "lb", "oz"]
MediaType = Literal["image", "video"]


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
    price_v2: "Price | None" = None
    media_v2: list["Media"] = field(default_factory=list)
    identifiers: dict[str, str] = field(default_factory=dict)

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
class Product:
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
    price_v2: "Price | None" = None
    media_v2: list["Media"] = field(default_factory=list)
    categories_v2: list[list[str]] = field(default_factory=list)
    identifiers: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

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


@dataclass
class OptionDef:
    name: str
    values: list[str] = field(default_factory=list)


@dataclass
class OptionValue:
    name: str
    value: str


@dataclass
class Inventory:
    track_quantity: bool | None = None
    quantity: int | None = None
    available: bool | None = None
    allow_backorder: bool | None = None


@dataclass
class Seo:
    title: str | None = None
    description: str | None = None


@dataclass
class SourceRef:
    platform: str
    id: str | None = None
    slug: str | None = None
    url: str | None = None


@dataclass
class CategorySet:
    paths: list[list[str]] = field(default_factory=list)
    primary: list[str] | None = None


@dataclass
class Identifiers:
    values: dict[str, str] = field(default_factory=dict)


__all__ = [
    "CategorySet",
    "Currency",
    "Identifiers",
    "Inventory",
    "Media",
    "MediaType",
    "Money",
    "OptionDef",
    "OptionValue",
    "Price",
    "Product",
    "Seo",
    "SourceRef",
    "Variant",
    "Weight",
    "WeightUnit",
]
