import csv
import io
from datetime import datetime, timezone
import re
from typing import Iterable

from ..canonical import (
    OptionDef,
    Product,
    Variant,
    resolve_all_image_urls as model_resolve_all_image_urls,
    resolve_current_money as model_resolve_current_money,
    resolve_option_defs as model_resolve_option_defs,
    resolve_primary_image_url as model_resolve_primary_image_url,
    resolve_taxonomy_paths as model_resolve_taxonomy_paths,
    resolve_variant_option_values as model_resolve_variant_option_values,
)

_SAFE_DEST_RE = re.compile(r"[^a-z0-9-]+")


def ordered_unique(items: Iterable[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = (item or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        values.append(cleaned)
    return values


def format_number(value: float | None, *, decimals: int) -> str:
    if value is None:
        return ""
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")


def dict_rows_to_csv(rows: list[dict[str, str]], columns: list[str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp_compact(now: datetime | None = None) -> str:
    dt = now or _utcnow()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def make_export_filename(destination: str, *, now: datetime | None = None) -> str:
    cleaned = (destination or "").strip().lower().replace("_", "-")
    cleaned = _SAFE_DEST_RE.sub("-", cleaned).strip("-")
    if not cleaned:
        cleaned = "export"
    return f"{cleaned}-{utc_timestamp_compact(now)}.csv"


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _coerce_non_negative_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _clean_identifier_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    cleaned: dict[str, str] = {}
    for key, raw in value.items():
        cleaned_key = _clean_text(key)
        cleaned_value = _clean_text(raw)
        if not cleaned_key or not cleaned_value:
            continue
        if cleaned_key in cleaned:
            continue
        cleaned[cleaned_key] = cleaned_value
    return cleaned


def _normalize_image_url(value: object) -> str | None:
    url = _clean_text(value)
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _resolve_media_image_urls(*, media: list[object], primary_first: bool) -> list[str]:
    primary: list[str] = []
    regular: list[str] = []
    for item in media:
        if getattr(item, "type", None) != "image":
            continue
        url = _normalize_image_url(getattr(item, "url", None))
        if not url:
            continue
        if primary_first and getattr(item, "is_primary", False):
            primary.append(url)
        regular.append(url)
    if primary_first:
        return ordered_unique(primary + regular)
    return ordered_unique(regular)


def resolve_price_amount(product: Product, variant: Variant | None = None) -> float | None:
    money = model_resolve_current_money(product, variant)
    if money is None or money.amount is None:
        return None
    try:
        return float(money.amount)
    except (TypeError, ValueError):
        return None


def resolve_price_currency(product: Product, variant: Variant | None = None) -> str | None:
    money = model_resolve_current_money(product, variant)
    if money is None:
        return None
    currency = _clean_text(money.currency)
    return currency or None


def resolve_primary_image_url(product: Product, variant: Variant | None = None) -> str:
    return model_resolve_primary_image_url(product, variant) or ""


def resolve_all_image_urls(product: Product) -> list[str]:
    return model_resolve_all_image_urls(product)


def resolve_product_image_urls(product: Product) -> list[str]:
    typed_urls = _resolve_media_image_urls(media=product.media, primary_first=True)
    return typed_urls


def resolve_variant_image_url(variant: Variant) -> str:
    typed_urls = _resolve_media_image_urls(media=variant.media, primary_first=True)
    if typed_urls:
        return typed_urls[0]
    return ""


def resolve_option_defs(product: Product) -> list[OptionDef]:
    return model_resolve_option_defs(product)


def resolve_variant_option_map(product: Product, variant: Variant) -> dict[str, str]:
    values_by_name: dict[str, str] = {}
    for option in model_resolve_variant_option_values(product, variant):
        if option.name in values_by_name:
            continue
        values_by_name[option.name] = option.value
    return values_by_name


def resolve_taxonomy_paths(product: Product) -> list[list[str]]:
    return model_resolve_taxonomy_paths(product)


def resolve_primary_category(product: Product, *, separator: str = " > ") -> str:
    paths = resolve_taxonomy_paths(product)
    if not paths:
        return ""
    return separator.join(paths[0])


def resolve_seo_title(product: Product) -> str:
    if product.seo:
        title = _clean_text(product.seo.title)
        if title:
            return title
    return ""


def resolve_seo_description(product: Product) -> str:
    if product.seo:
        description = _clean_text(product.seo.description)
        if description:
            return description
    return ""


def resolve_variant_track_quantity(product: Product, variant: Variant) -> bool:
    if variant.inventory and variant.inventory.track_quantity is not None:
        return bool(variant.inventory.track_quantity)
    return bool(product.track_quantity)


def resolve_variant_inventory_quantity(variant: Variant) -> int | None:
    if variant.inventory and variant.inventory.quantity is not None:
        return _coerce_non_negative_int(variant.inventory.quantity)
    return None


def resolve_variant_available(variant: Variant) -> bool | None:
    if variant.inventory and variant.inventory.available is not None:
        return bool(variant.inventory.available)
    return None


def resolve_variant_allow_backorder(variant: Variant) -> bool | None:
    if variant.inventory and variant.inventory.allow_backorder is not None:
        return bool(variant.inventory.allow_backorder)
    return None


def resolve_identifier_values(product: Product, *, variant: Variant | None = None) -> dict[str, str]:
    if variant:
        return _clean_identifier_map(variant.identifiers.values)

    return _clean_identifier_map(product.identifiers.values)


def resolve_identifier_value(
    product: Product,
    key: str,
    *,
    variant: Variant | None = None,
) -> str | None:
    cleaned_key = _clean_text(key)
    if not cleaned_key:
        return None
    values = resolve_identifier_values(product, variant=variant)
    return values.get(cleaned_key)


def resolve_variants(product: Product) -> list[Variant]:
    variants = list(product.variants or [])
    if variants:
        return variants

    default_price = None
    if product.price and product.price.current.amount is not None:
        try:
            default_price = float(product.price.current.amount)
        except (TypeError, ValueError):
            default_price = None

    return [
        Variant(
            id=product.source.id,
            price={
                "amount": default_price,
                "currency": product.price.current.currency if product.price else None,
            },
            weight=product.weight,
        )
    ]


def resolve_weight_grams(product: Product, variant: Variant | None = None) -> float | None:
    candidate = variant.weight if variant and variant.weight is not None else product.weight
    if candidate is None or candidate.value is None:
        return None
    try:
        value = float(candidate.value)
    except (TypeError, ValueError):
        return None
    unit = str(candidate.unit or "g").lower()
    if unit == "kg":
        return value * 1000.0
    if unit == "lb":
        return value * 453.59237
    if unit == "oz":
        return value * 28.349523125
    return value


def convert_weight_from_grams(value_grams: float | None, *, unit: str) -> float | None:
    if value_grams is None:
        return None
    try:
        grams = float(value_grams)
    except (TypeError, ValueError):
        return None

    target = str(unit or "g").strip().lower()
    if target == "kg":
        return grams / 1000.0
    if target == "lb":
        return grams / 453.59237
    if target == "oz":
        return grams / 28.349523125
    return grams
