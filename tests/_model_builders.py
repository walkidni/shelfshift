from __future__ import annotations

from typing import Any

from app.models import (
    CategorySet,
    Inventory,
    Media,
    OptionValue,
    Product as CanonicalProduct,
    Seo,
    SourceRef,
    Variant as CanonicalVariant,
)


def _pop_optional_str(kwargs: dict[str, Any], key: str) -> str | None:
    value = kwargs.pop(key, None)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _build_source(kwargs: dict[str, Any]) -> SourceRef:
    source = kwargs.get("source")
    if source is not None:
        return source
    return SourceRef(
        platform=str(kwargs.pop("platform", "unknown") or "unknown"),
        id=_pop_optional_str(kwargs, "id"),
        slug=_pop_optional_str(kwargs, "slug"),
        url=_pop_optional_str(kwargs, "url"),
    )


def _build_seo(kwargs: dict[str, Any]) -> Seo | None:
    if kwargs.get("seo") is not None:
        return kwargs.get("seo")
    meta_title = kwargs.pop("meta_title", None)
    meta_description = kwargs.pop("meta_description", None)
    if meta_title is None and meta_description is None:
        return None
    return Seo(title=meta_title, description=meta_description)


def _build_taxonomy(kwargs: dict[str, Any]) -> CategorySet | None:
    if kwargs.get("taxonomy") is not None:
        return kwargs.get("taxonomy")
    category = kwargs.pop("category", None)
    if not category:
        return None
    category_text = str(category).strip()
    if not category_text:
        return None
    return CategorySet(paths=[[category_text]], primary=[category_text])


def _build_media_from_images(images: Any) -> list[Media]:
    if not isinstance(images, list):
        return []
    media: list[Media] = []
    for idx, image in enumerate(images, start=1):
        url = str(image or "").strip()
        if not url:
            continue
        media.append(
            Media(
                url=url,
                type="image",
                position=idx,
                is_primary=(idx == 1),
            )
        )
    return media


def Product(**kwargs: Any) -> CanonicalProduct:
    normalized = dict(kwargs)

    source = _build_source(normalized)
    seo = _build_seo(normalized)
    taxonomy = _build_taxonomy(normalized)

    images = normalized.pop("images", None)
    if normalized.get("media") is None and images is not None:
        normalized["media"] = _build_media_from_images(images)

    normalized["source"] = source
    if seo is not None:
        normalized["seo"] = seo
    if taxonomy is not None:
        normalized["taxonomy"] = taxonomy

    return CanonicalProduct(**normalized)


def Variant(**kwargs: Any) -> CanonicalVariant:
    normalized = dict(kwargs)

    options = normalized.pop("options", None)
    if normalized.get("option_values") is None and isinstance(options, dict):
        normalized["option_values"] = [
            OptionValue(name=str(name), value=str(value))
            for name, value in options.items()
            if str(name).strip() and str(value).strip()
        ]

    price_amount = normalized.pop("price_amount", None)
    currency = normalized.pop("currency", None)
    if normalized.get("price") is None and (price_amount is not None or currency is not None):
        normalized["price"] = {
            "amount": price_amount,
            "currency": currency,
        }

    inventory_quantity = normalized.pop("inventory_quantity", None)
    available = normalized.pop("available", None)
    inventory = normalized.get("inventory")
    if inventory is None and (inventory_quantity is not None or available is not None):
        normalized["inventory"] = Inventory(
            track_quantity=True if inventory_quantity is not None else None,
            quantity=inventory_quantity,
            available=available if isinstance(available, bool) else None,
        )
    elif isinstance(inventory, dict):
        if inventory_quantity is not None and "quantity" not in inventory:
            inventory["quantity"] = inventory_quantity
        if isinstance(available, bool) and "available" not in inventory:
            inventory["available"] = available
        normalized["inventory"] = inventory
    elif isinstance(inventory, Inventory) and isinstance(available, bool) and inventory.available is None:
        inventory.available = available
        normalized["inventory"] = inventory

    image = normalized.pop("image", None)
    if normalized.get("media") is None and image:
        normalized["media"] = [
            Media(
                url=str(image),
                type="image",
                position=1,
                is_primary=True,
                variant_skus=[str(normalized.get("sku"))] if normalized.get("sku") else [],
            )
        ]

    return CanonicalVariant(**normalized)
