from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any, Iterable

from .entities import Media, Money, OptionDef, OptionValue, Product, Variant

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


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ordered_unique_strings(items: Iterable[Any]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = _clean_text(item)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        values.append(cleaned)
    return values


def _iter_option_values(raw_values: Any) -> list[Any]:
    if isinstance(raw_values, set):
        return sorted(raw_values, key=str)
    if isinstance(raw_values, (list, tuple)):
        return list(raw_values)
    if raw_values is None:
        return []
    return [raw_values]


def resolve_option_defs(product: Product) -> list[OptionDef]:
    if product.options_v2:
        resolved: list[OptionDef] = []
        for option in product.options_v2:
            name = _clean_text(option.name)
            if not name:
                continue
            values = _ordered_unique_strings(option.values)
            resolved.append(OptionDef(name=name, values=values))
        return resolved

    values_by_name: dict[str, list[str]] = {}
    ordered_names: list[str] = []

    def _ensure_name(name: str) -> None:
        if name in values_by_name:
            return
        values_by_name[name] = []
        ordered_names.append(name)

    def _add_value(name: str, value: Any) -> None:
        cleaned = _clean_text(value)
        if not cleaned:
            return
        bucket = values_by_name[name]
        if cleaned not in bucket:
            bucket.append(cleaned)

    for raw_name, raw_values in (product.options or {}).items():
        name = _clean_text(raw_name)
        if not name:
            continue
        _ensure_name(name)
        for raw_value in _iter_option_values(raw_values):
            _add_value(name, raw_value)

    for variant in product.variants:
        for raw_name, raw_value in (variant.options or {}).items():
            name = _clean_text(raw_name)
            if not name:
                continue
            _ensure_name(name)
            _add_value(name, raw_value)

    return [OptionDef(name=name, values=values_by_name[name]) for name in ordered_names]


def resolve_variant_option_values(product: Product, variant: Variant) -> list[OptionValue]:
    if variant.option_values_v2:
        resolved: list[OptionValue] = []
        seen: set[str] = set()
        for option in variant.option_values_v2:
            name = _clean_text(option.name)
            value = _clean_text(option.value)
            if not name or not value or name in seen:
                continue
            seen.add(name)
            resolved.append(OptionValue(name=name, value=value))
        return resolved

    ordered_defs = [option.name for option in resolve_option_defs(product)]
    variant_pairs: list[tuple[str, str]] = []
    seen_names: set[str] = set()
    for raw_name, raw_value in (variant.options or {}).items():
        name = _clean_text(raw_name)
        value = _clean_text(raw_value)
        if not name or not value or name in seen_names:
            continue
        seen_names.add(name)
        variant_pairs.append((name, value))

    by_name = {name: value for name, value in variant_pairs}
    resolved: list[OptionValue] = []
    emitted: set[str] = set()
    for name in ordered_defs:
        value = by_name.get(name)
        if value is None:
            continue
        emitted.add(name)
        resolved.append(OptionValue(name=name, value=value))

    for name, value in variant_pairs:
        if name in emitted:
            continue
        resolved.append(OptionValue(name=name, value=value))

    return resolved


def _normalize_paths(raw_paths: Any) -> list[list[str]]:
    if not isinstance(raw_paths, list):
        return []

    normalized: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for raw_path in raw_paths:
        if not isinstance(raw_path, (list, tuple)):
            continue
        path = _ordered_unique_strings(raw_path)
        if not path:
            continue
        key = tuple(path)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(path)
    return normalized


def _path_from_category_string(value: Any) -> list[list[str]]:
    category = _clean_text(value)
    if not category:
        return []
    return [[category]]


def resolve_taxonomy_paths(product: Product) -> list[list[str]]:
    if product.taxonomy_v2 is not None:
        typed_paths = _normalize_paths(product.taxonomy_v2.paths)
        if typed_paths:
            return typed_paths
        if product.taxonomy_v2.primary:
            primary = _ordered_unique_strings(product.taxonomy_v2.primary)
            if primary:
                return [primary]

    categories_v2_paths = _normalize_paths(product.categories_v2)
    if categories_v2_paths:
        return categories_v2_paths

    return _path_from_category_string(product.category)


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
    "resolve_option_defs",
    "resolve_primary_image_url",
    "resolve_taxonomy_paths",
    "resolve_variant_option_values",
]
