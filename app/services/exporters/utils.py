import csv
import io
from datetime import datetime, timezone
import re
from typing import Iterable

from app.models import (
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
    if product.seo_v2:
        title = _clean_text(product.seo_v2.title)
        if title:
            return title
    return _clean_text(product.meta_title)


def resolve_seo_description(product: Product) -> str:
    if product.seo_v2:
        description = _clean_text(product.seo_v2.description)
        if description:
            return description
    return _clean_text(product.meta_description)


def resolve_variant_track_quantity(product: Product, variant: Variant) -> bool:
    if variant.inventory_v2 and variant.inventory_v2.track_quantity is not None:
        return bool(variant.inventory_v2.track_quantity)
    if variant.inventory_quantity is not None:
        return True
    return bool(product.track_quantity)


def resolve_variant_inventory_quantity(variant: Variant) -> int | None:
    if variant.inventory_v2 and variant.inventory_v2.quantity is not None:
        return _coerce_non_negative_int(variant.inventory_v2.quantity)
    return _coerce_non_negative_int(variant.inventory_quantity)


def resolve_variant_available(variant: Variant) -> bool | None:
    if variant.inventory_v2 and variant.inventory_v2.available is not None:
        return bool(variant.inventory_v2.available)
    if variant.available is not None:
        return bool(variant.available)
    return None


def resolve_variant_allow_backorder(variant: Variant) -> bool | None:
    if variant.inventory_v2 and variant.inventory_v2.allow_backorder is not None:
        return bool(variant.inventory_v2.allow_backorder)
    return None


def resolve_identifier_values(product: Product, *, variant: Variant | None = None) -> dict[str, str]:
    if variant:
        typed_values = _clean_identifier_map(
            variant.identifiers_v2.values if variant.identifiers_v2 else None
        )
        if typed_values:
            return typed_values
        return _clean_identifier_map(variant.identifiers)

    typed_values = _clean_identifier_map(product.identifiers_v2.values if product.identifiers_v2 else None)
    if typed_values:
        return typed_values
    return _clean_identifier_map(product.identifiers)


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
    if isinstance(product.price, dict) and isinstance(product.price.get("amount"), (int, float)):
        default_price = float(product.price["amount"])

    return [Variant(id=product.id, price_amount=default_price, weight=product.weight)]
