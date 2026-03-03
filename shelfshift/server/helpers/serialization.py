"""Server-only canonical payload serializers."""

from typing import Any

from ...core.canonical.entities import Product


def serialize_product_for_api(product: Product, *, include_raw: bool) -> dict[str, Any]:
    return product.to_dict(include_raw=include_raw)


__all__ = ["serialize_product_for_api"]
