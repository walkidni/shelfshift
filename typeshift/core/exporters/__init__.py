"""Core CSV exporters."""

from __future__ import annotations

from app.models import Product
from app.services.exporters import (
    product_to_bigcommerce_csv,
    product_to_shopify_csv,
    product_to_squarespace_csv,
    product_to_wix_csv,
    product_to_woocommerce_csv,
)
from app.services.exporters.weight_units import resolve_weight_unit


def export_csv_for_target(
    product: Product,
    *,
    target_platform: str,
    publish: bool = False,
    weight_unit: str = "",
    bigcommerce_csv_format: str = "modern",
    squarespace_product_page: str = "",
    squarespace_product_url: str = "",
) -> tuple[str, str]:
    target = (target_platform or "").strip().lower()
    resolved_weight_unit = resolve_weight_unit(target, weight_unit)

    if target == "shopify":
        return product_to_shopify_csv(product, publish=publish, weight_unit=resolved_weight_unit)
    if target == "bigcommerce":
        return product_to_bigcommerce_csv(
            product,
            publish=publish,
            csv_format=bigcommerce_csv_format,
            weight_unit=resolved_weight_unit,
        )
    if target == "wix":
        return product_to_wix_csv(product, publish=publish, weight_unit=resolved_weight_unit)
    if target == "squarespace":
        return product_to_squarespace_csv(
            product,
            publish=publish,
            product_page=squarespace_product_page,
            product_url=squarespace_product_url,
            weight_unit=resolved_weight_unit,
        )
    if target == "woocommerce":
        return product_to_woocommerce_csv(product, publish=publish, weight_unit=resolved_weight_unit)
    raise ValueError(
        "target_platform must be one of: shopify, bigcommerce, wix, squarespace, woocommerce"
    )


__all__ = ["export_csv_for_target"]
