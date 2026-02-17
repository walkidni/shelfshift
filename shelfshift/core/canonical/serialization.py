from typing import Any

from .entities import Product, Variant


def serialize_variant_for_api(variant: Variant, *, include_raw: bool) -> dict[str, Any]:
    return variant.to_dict(include_raw=include_raw)


def serialize_product_for_api(product: Product, *, include_raw: bool) -> dict[str, Any]:
    return product.to_dict(include_raw=include_raw)


__all__ = [
    "serialize_product_for_api",
    "serialize_variant_for_api",
]
