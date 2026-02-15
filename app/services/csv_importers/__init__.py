from app.models import Product

from .batch import import_products_from_csv
from .bigcommerce import parse_bigcommerce_csv
from .common import MAX_CSV_UPLOAD_BYTES, decode_csv_bytes, parse_canonical_product_payload
from .shopify import parse_shopify_csv
from .squarespace import parse_squarespace_csv
from .wix import parse_wix_csv
from .woocommerce import parse_woocommerce_csv


_WEIGHT_UNIT_REQUIRED_PLATFORMS = {"bigcommerce", "wix", "squarespace"}


def import_product_from_csv(
    *,
    source_platform: str,
    csv_bytes: bytes,
    source_weight_unit: str | None = None,
) -> Product:
    platform = str(source_platform or "").strip().lower()
    if platform not in {"shopify", "bigcommerce", "wix", "squarespace", "woocommerce"}:
        raise ValueError(
            "source_platform must be one of: shopify, bigcommerce, wix, squarespace, woocommerce"
        )
    if not csv_bytes:
        raise ValueError("CSV file is empty.")
    if len(csv_bytes) > MAX_CSV_UPLOAD_BYTES:
        raise ValueError("CSV file exceeds 5 MB limit.")

    resolved_weight_unit = str(source_weight_unit or "").strip().lower()
    if platform in _WEIGHT_UNIT_REQUIRED_PLATFORMS and not resolved_weight_unit:
        raise ValueError(f"source_weight_unit is required for {platform} CSV imports.")
    if resolved_weight_unit and resolved_weight_unit not in {"g", "kg", "lb", "oz"}:
        raise ValueError("source_weight_unit must be one of: g, kg, lb, oz.")

    csv_text = decode_csv_bytes(csv_bytes)
    if platform == "shopify":
        return parse_shopify_csv(csv_text)
    if platform == "woocommerce":
        return parse_woocommerce_csv(csv_text)
    if platform == "squarespace":
        return parse_squarespace_csv(csv_text, source_weight_unit=resolved_weight_unit)
    if platform == "wix":
        return parse_wix_csv(csv_text, source_weight_unit=resolved_weight_unit)
    return parse_bigcommerce_csv(csv_text, source_weight_unit=resolved_weight_unit)


__all__ = [
    "MAX_CSV_UPLOAD_BYTES",
    "import_product_from_csv",
    "import_products_from_csv",
    "parse_canonical_product_payload",
]
