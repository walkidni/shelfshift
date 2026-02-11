import re
from dataclasses import dataclass
from typing import Any, Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def http_session(timeout: int = 20) -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    # store desired default timeout on the session for convenience
    s.request_timeout = timeout  # type: ignore[attr-defined]
    return s


@dataclass
class Variant:
    id: str | None = None
    sku: str | None = None
    title: str | None = None
    options: dict[str, str] | None = None  # e.g. {"Color": "Black", "Size": "M"}
    price_amount: float | None = None
    currency: str | None = None
    image: str | None = None
    available: bool | None = None
    inventory_quantity: int | None = None
    weight: float | None = None  # For shipping calculations
    raw: dict[str, Any] | None = None

    def __post_init__(self):
        if self.options is None:
            self.options = {}

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
    images: list[str] | None
    raw: dict[str, Any] | None
    options: dict[str, list[str]] | None = None  # {"Color": ["Black","White"], "Size": ["S","M"]}
    variants: list[Variant] | None = None
    brand: str | None = None  # Product brand for metadata
    category: str | None = None  # Product category for SEO and organization
    meta_title: str | None = None  # Custom page title for SEO
    meta_description: str | None = None  # Custom meta description for SEO
    slug: str | None = None  # Source URL slug if available
    tags: list[str] | None = None  # Tags for searchability
    vendor: str | None = None  # Vendor/supplier name
    weight: float | None = None  # Default product weight
    requires_shipping: bool = True  # Whether product needs shipping
    track_quantity: bool = True  # Whether to track inventory
    is_digital: bool = False  # Digital product flag

    def __post_init__(self):
        if self.options is None:
            self.options = {}
        if self.variants is None:
            self.variants = []
        if self.images is None:
            self.images = []
        if self.tags is None:
            self.tags = []

    def to_dict(self, include_raw: bool = True) -> dict[str, Any]:
        data = {
            "platform": self.platform,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "images": self.images,
            "options": self.options or {},
            "variants": [v.to_dict(include_raw=include_raw) for v in (self.variants or [])],
            "brand": self.brand,
            "category": self.category,
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "slug": self.slug,
            "tags": self.tags or [],
            "vendor": self.vendor,
            "weight": self.weight,
            "requires_shipping": self.requires_shipping,
            "track_quantity": self.track_quantity,
            "is_digital": self.is_digital,
        }
        if include_raw:
            data["raw"] = self.raw
        return data


class ProductClient:
    platform: str = "generic"

    def fetch_product(self, url: str) -> ProductResult:
        raise NotImplementedError


@dataclass
class ApiConfig:
    """
    Minimal configuration for RapidAPI-backed clients.
    Hosts/endpoints are hardcoded in the clients.
    """

    rapidapi_key: str | None = None
    amazon_country: str = "US"  # used by the Amazon provider


def dedupe(seq: Iterable[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for x in seq:
        if isinstance(x, str) and x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def parse_money_to_float(x: Any) -> float | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        try:
            return float(x)
        except Exception:
            return None
    if isinstance(x, str):
        s = x.strip()
        s = s.replace(",", "")
        s = re.sub(r"[^\d\.]", "", s)  # drop currency symbols/letters
        try:
            return float(s) if s else None
        except Exception:
            return None
    return None


def append_default_variant_if_empty(variants: list[Variant], default_variant: Variant | None) -> None:
    if variants or default_variant is None:
        return
    variants.append(default_variant)


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    cleaned = _HTML_TAG_RE.sub(" ", text or "")
    return " ".join(cleaned.split())


def truncate(text: str, limit: int = 400) -> str:
    return (text or "")[:limit].strip()


def meta_from_description(
    title: str,
    description: str | None,
    *,
    strip_html_content: bool,
) -> tuple[str, str | None]:
    if not description:
        return title, None
    base = strip_html(description) if strip_html_content else description
    return title, truncate(base)
