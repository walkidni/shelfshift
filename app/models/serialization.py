from typing import Any, Literal

from .entities import (
    Identifiers,
    Inventory,
    Media,
    Money,
    Price,
    Product,
    Variant,
)
from .helpers import (
    format_decimal,
    normalize_currency,
    resolve_all_image_urls,
    resolve_current_money,
    resolve_option_defs,
    resolve_taxonomy_paths,
    resolve_variant_option_values,
)

ResponseProfile = Literal["typed", "legacy"]


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_url(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.startswith("//"):
        return f"https:{text}"
    return text


def _clean_identifier_values(values: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in (values or {}).items():
        key_str = _clean_text(key)
        value_str = _clean_text(value)
        if not key_str or not value_str:
            continue
        out[key_str] = value_str
    return out


def _identifier_payload(typed: Identifiers | None, legacy: dict[str, str]) -> dict[str, dict[str, str]]:
    if typed is not None:
        return {"values": _clean_identifier_values(typed.values)}
    return {"values": _clean_identifier_values(legacy)}


def _serialize_money(value: Money | None) -> dict[str, str | None] | None:
    if value is None:
        return None
    amount = format_decimal(value.amount) if value.amount is not None else None
    if amount == "":
        amount = None
    currency = normalize_currency(value.currency)
    if amount is None and currency is None:
        return None
    return {
        "amount": amount,
        "currency": currency,
    }


def _serialize_price(value: Price | None) -> dict[str, Any] | None:
    if value is None:
        return None
    current = _serialize_money(value.current)
    compare_at = _serialize_money(value.compare_at)
    cost = _serialize_money(value.cost)
    min_price = _serialize_money(value.min_price)
    max_price = _serialize_money(value.max_price)

    if current is None and compare_at is None and cost is None and min_price is None and max_price is None:
        return None

    return {
        "current": current,
        "compare_at": compare_at,
        "cost": cost,
        "min_price": min_price,
        "max_price": max_price,
    }


def _resolve_product_price(product: Product) -> dict[str, Any] | None:
    if product.price_v2 is not None:
        return _serialize_price(product.price_v2)

    fallback_money = resolve_current_money(product, variant=None)
    if fallback_money is None:
        return None
    return _serialize_price(Price(current=fallback_money))


def _resolve_variant_price(product: Product, variant: Variant) -> dict[str, Any] | None:
    if variant.price_v2 is not None:
        return _serialize_price(variant.price_v2)

    fallback_money = resolve_current_money(product, variant=variant)
    if fallback_money is None:
        return None
    return _serialize_price(Price(current=fallback_money))


def _dedupe_media(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (str(item.get("type") or "image"), str(item.get("url") or ""))
        if not key[1] or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _serialize_typed_media(items: list[Media]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        url = _normalize_url(item.url)
        if not url:
            continue
        media_type = item.type if item.type in {"image", "video"} else "image"
        out.append(
            {
                "url": url,
                "type": media_type,
                "alt": _clean_text(item.alt),
                "position": item.position,
                "is_primary": item.is_primary,
                "variant_skus": [_clean_text(sku) for sku in item.variant_skus if _clean_text(sku)],
            }
        )
    return _dedupe_media(out)


def _serialize_fallback_media(urls: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw_url in urls:
        url = _normalize_url(raw_url)
        if not url:
            continue
        out.append(
            {
                "url": url,
                "type": "image",
                "alt": None,
                "position": None,
                "is_primary": None,
                "variant_skus": [],
            }
        )
    return _dedupe_media(out)


def _resolve_product_media(product: Product) -> list[dict[str, Any]]:
    if product.media_v2:
        return _serialize_typed_media(product.media_v2)
    return _serialize_fallback_media(resolve_all_image_urls(product))


def _resolve_variant_media(variant: Variant) -> list[dict[str, Any]]:
    if variant.media_v2:
        return _serialize_typed_media(variant.media_v2)

    fallback_url = _normalize_url(variant.image)
    if not fallback_url:
        return []
    return _serialize_fallback_media([fallback_url])


def _resolve_taxonomy_payload(product: Product) -> dict[str, Any]:
    paths = [list(path) for path in resolve_taxonomy_paths(product)]
    primary: list[str] | None = None
    if product.taxonomy_v2 is not None and product.taxonomy_v2.primary:
        primary = [item for item in (str(part).strip() for part in product.taxonomy_v2.primary) if item]
    if primary is None and paths:
        primary = list(paths[0])
    return {
        "paths": paths,
        "primary": primary,
    }


def _resolve_source_payload(product: Product) -> dict[str, Any]:
    if product.source_v2 is not None:
        platform = _clean_text(product.source_v2.platform) or product.platform
        return {
            "platform": platform,
            "id": product.source_v2.id,
            "slug": product.source_v2.slug,
            "url": _normalize_url(product.source_v2.url),
        }
    return {
        "platform": product.platform,
        "id": product.id,
        "slug": product.slug,
        "url": None,
    }


def _resolve_seo_payload(product: Product) -> dict[str, str | None]:
    if product.seo_v2 is not None:
        return {
            "title": product.seo_v2.title,
            "description": product.seo_v2.description,
        }
    return {
        "title": product.meta_title,
        "description": product.meta_description,
    }


def _resolve_variant_inventory(product: Product, variant: Variant) -> dict[str, Any]:
    inventory: Inventory | None = variant.inventory_v2
    if inventory is not None:
        return {
            "track_quantity": inventory.track_quantity,
            "quantity": inventory.quantity,
            "available": inventory.available,
            "allow_backorder": inventory.allow_backorder,
        }
    return {
        "track_quantity": product.track_quantity,
        "quantity": variant.inventory_quantity,
        "available": variant.available,
        "allow_backorder": None,
    }


def serialize_variant_for_api(product: Product, variant: Variant) -> dict[str, Any]:
    option_values = resolve_variant_option_values(product, variant)
    return {
        "id": variant.id,
        "sku": variant.sku,
        "title": variant.title,
        "option_values": [{"name": item.name, "value": item.value} for item in option_values],
        "price": _resolve_variant_price(product, variant),
        "available": variant.available,
        "inventory": _resolve_variant_inventory(product, variant),
        "weight": variant.weight,
        "media": _resolve_variant_media(variant),
        "identifiers": _identifier_payload(variant.identifiers_v2, variant.identifiers),
    }


def _serialize_typed_product_for_api(product: Product, *, include_raw: bool) -> dict[str, Any]:
    option_defs = resolve_option_defs(product)
    payload = {
        "source": _resolve_source_payload(product),
        "title": product.title,
        "description": product.description,
        "seo": _resolve_seo_payload(product),
        "brand": product.brand,
        "vendor": product.vendor,
        "taxonomy": _resolve_taxonomy_payload(product),
        "tags": list(product.tags),
        "options": [{"name": item.name, "values": list(item.values)} for item in option_defs],
        "variants": [serialize_variant_for_api(product, variant) for variant in product.variants],
        "price": _resolve_product_price(product),
        "weight": product.weight,
        "requires_shipping": product.requires_shipping,
        "track_quantity": product.track_quantity,
        "is_digital": product.is_digital,
        "media": _resolve_product_media(product),
        "identifiers": _identifier_payload(product.identifiers_v2, product.identifiers),
        "provenance": dict(product.provenance),
    }
    if include_raw:
        payload["raw"] = product.raw
    return payload


def serialize_product_for_api(
    product: Product,
    *,
    profile: ResponseProfile,
    include_raw: bool,
) -> dict[str, Any]:
    if profile == "legacy":
        return product.to_dict(include_raw=include_raw)
    return _serialize_typed_product_for_api(product, include_raw=include_raw)


__all__ = [
    "ResponseProfile",
    "serialize_product_for_api",
    "serialize_variant_for_api",
]
