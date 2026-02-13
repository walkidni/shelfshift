from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any

from .entities import Media, Money, Product, Variant

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


def _build_money(amount: Decimal | None, currency: str | None) -> Money | None:
    if amount is None and currency is None:
        return None
    return Money(amount=amount, currency=currency)


def resolve_current_money(product: Product, variant: Variant | None = None) -> Money | None:
    if variant and variant.price_v2:
        money = variant.price_v2.current
        return _build_money(money.amount, normalize_currency(money.currency))

    if product.price_v2:
        money = product.price_v2.current
        return _build_money(money.amount, normalize_currency(money.currency))

    if variant:
        variant_money = _build_money(
            parse_decimal_money(variant.price_amount),
            normalize_currency(variant.currency),
        )
        if variant_money is not None:
            return variant_money

    product_price = product.price if isinstance(product.price, dict) else {}
    return _build_money(
        parse_decimal_money(product_price.get("amount")),
        normalize_currency(product_price.get("currency")),
    )


def _normalized_image_url(url: Any) -> str | None:
    if not isinstance(url, str):
        return None
    stripped = url.strip()
    if not stripped:
        return None
    if stripped.startswith("//"):
        return f"https:{stripped}"
    return stripped


def _media_image_urls(media: list[Media]) -> list[str]:
    urls: list[str] = []
    for item in media:
        if item.type != "image":
            continue
        url = _normalized_image_url(item.url)
        if url:
            urls.append(url)
    return urls


def _first_primary_media_url(media: list[Media]) -> str | None:
    primary_urls: list[str] = []
    fallback_urls: list[str] = []
    for item in media:
        if item.type != "image":
            continue
        url = _normalized_image_url(item.url)
        if not url:
            continue
        if item.is_primary:
            primary_urls.append(url)
        fallback_urls.append(url)
    if primary_urls:
        return primary_urls[0]
    if fallback_urls:
        return fallback_urls[0]
    return None


def resolve_primary_image_url(product: Product, variant: Variant | None = None) -> str | None:
    if variant:
        variant_primary = _first_primary_media_url(variant.media_v2)
        if variant_primary:
            return variant_primary

        variant_image = _normalized_image_url(variant.image)
        if variant_image:
            return variant_image

    product_primary = _first_primary_media_url(product.media_v2)
    if product_primary:
        return product_primary

    all_urls = resolve_all_image_urls(product)
    return all_urls[0] if all_urls else None


def resolve_all_image_urls(product: Product) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def _append(url: str | None) -> None:
        if not url or url in seen:
            return
        seen.add(url)
        urls.append(url)

    for url in _media_image_urls(product.media_v2):
        _append(url)
    for url in product.images:
        _append(_normalized_image_url(url))

    for variant in product.variants:
        for url in _media_image_urls(variant.media_v2):
            _append(url)
        _append(_normalized_image_url(variant.image))

    return urls


__all__ = [
    "format_decimal",
    "normalize_currency",
    "parse_decimal_money",
    "resolve_all_image_urls",
    "resolve_current_money",
    "resolve_primary_image_url",
]
