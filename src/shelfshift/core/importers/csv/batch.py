import csv
import io

from ...canonical import Product
from .bigcommerce import parse_bigcommerce_csv
from .common import (
    csv_rows,
    decode_csv_bytes,
)
from .shopify import (
    extract_shopify_handles,
    parse_shopify_csv,
    require_shopify_headers,
    shopify_row_handle,
)
from .squarespace import parse_squarespace_csv
from .wix import parse_wix_csv
from .woocommerce import parse_woocommerce_csv


def _patch_batch_provenance(
    products: list[Product],
    *,
    detected_product_count: int,
) -> None:
    """Update csv_import provenance on each product to reflect the full batch context."""
    for product in products:
        provenance = dict(product.provenance or {})
        csv_import = dict(provenance.get("csv_import") or {})
        csv_import["detected_product_count"] = detected_product_count
        csv_import["selection_policy"] = "batch_all"
        provenance["csv_import"] = csv_import
        product.provenance = provenance


_WEIGHT_UNIT_REQUIRED_PLATFORMS = {"bigcommerce", "wix", "squarespace"}
_WEIGHT_UNIT_ALLOWLIST = {"g", "kg", "lb", "oz"}


def import_products_from_csv(
    *,
    source_platform: str,
    csv_bytes: bytes,
    source_weight_unit: str | None = None,
) -> list[Product]:
    platform = str(source_platform or "").strip().lower()
    if platform not in {"shopify", "bigcommerce", "wix", "squarespace", "woocommerce"}:
        raise ValueError(
            "source_platform must be one of: shopify, bigcommerce, wix, squarespace, woocommerce"
        )
    if not csv_bytes:
        raise ValueError("CSV file is empty.")

    resolved_weight_unit = str(source_weight_unit or "").strip().lower()
    if platform in _WEIGHT_UNIT_REQUIRED_PLATFORMS and not resolved_weight_unit:
        raise ValueError(f"source_weight_unit is required for {platform} CSV imports.")
    if resolved_weight_unit and resolved_weight_unit not in _WEIGHT_UNIT_ALLOWLIST:
        raise ValueError("source_weight_unit must be one of: g, kg, lb, oz.")

    csv_text = decode_csv_bytes(csv_bytes)

    if platform == "shopify":
        return parse_shopify_csv_batch(csv_text, source_platform=platform)
    if platform == "wix":
        return parse_wix_csv_batch(csv_text, source_weight_unit=resolved_weight_unit)
    if platform == "squarespace":
        return parse_squarespace_csv_batch(csv_text, source_weight_unit=resolved_weight_unit)
    if platform == "woocommerce":
        return parse_woocommerce_csv_batch(csv_text)
    return parse_bigcommerce_csv_batch(csv_text, source_weight_unit=resolved_weight_unit)


def _rows_to_csv_text(headers: list[str], rows: list[dict[str, str]]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return out.getvalue()


def parse_shopify_csv_batch(csv_text: str, *, source_platform: str = "shopify") -> list[Product]:
    headers, rows = csv_rows(csv_text)
    require_shopify_headers(headers)

    handles = extract_shopify_handles(rows)
    if not handles:
        raise ValueError("Shopify CSV must include at least one row with Handle or URL handle.")

    products: list[Product] = []
    for selected_handle in handles:
        selected_rows = [row for row in rows if shopify_row_handle(row) == selected_handle]
        if not selected_rows:
            continue
        segment_csv = _rows_to_csv_text(headers, selected_rows)
        products.append(parse_shopify_csv(segment_csv, source_platform=source_platform))

    _patch_batch_provenance(products, detected_product_count=len(handles))
    return products


def parse_wix_csv_batch(csv_text: str, *, source_weight_unit: str) -> list[Product]:
    headers, rows = csv_rows(csv_text)
    # Let the single-product parser validate required headers per group.
    handles: list[str] = []
    for row in rows:
        handle = str(row.get("handle") or "").strip()
        if not handle:
            continue
        if handle not in handles:
            handles.append(handle)
    if not handles:
        raise ValueError("Wix CSV must include at least one row with handle.")

    products: list[Product] = []
    for handle in handles:
        selected_rows = [row for row in rows if str(row.get("handle") or "").strip() == handle]
        segment_csv = _rows_to_csv_text(headers, selected_rows)
        products.append(parse_wix_csv(segment_csv, source_weight_unit=source_weight_unit))
    _patch_batch_provenance(products, detected_product_count=len(handles))
    return products


def parse_squarespace_csv_batch(csv_text: str, *, source_weight_unit: str) -> list[Product]:
    headers, rows = csv_rows(csv_text)
    # Squarespace exports anchor product boundaries on non-empty Title rows.
    anchors = [index for index, row in enumerate(rows) if str(row.get("Title") or "").strip()]
    if not anchors:
        # Single-product parser will error if it's not valid, but keep behavior consistent.
        return [parse_squarespace_csv(csv_text, source_weight_unit=source_weight_unit)]

    products: list[Product] = []
    for idx, start in enumerate(anchors):
        end = anchors[idx + 1] if idx + 1 < len(anchors) else len(rows)
        segment_rows = rows[start:end]
        segment_csv = _rows_to_csv_text(headers, segment_rows)
        products.append(parse_squarespace_csv(segment_csv, source_weight_unit=source_weight_unit))
    _patch_batch_provenance(products, detected_product_count=len(anchors))
    return products


def parse_woocommerce_csv_batch(csv_text: str) -> list[Product]:
    headers, rows = csv_rows(csv_text)
    product_rows: list[dict[str, str]] = [
        row for row in rows if str(row.get("Type") or "").strip().lower() in {"simple", "variable"}
    ]
    if not product_rows:
        raise ValueError(
            "WooCommerce CSV must include at least one simple or variable product row."
        )

    products: list[Product] = []
    for product_row in product_rows:
        parent_sku = str(product_row.get("SKU") or "").strip()
        selected_rows = [product_row]
        if str(product_row.get("Type") or "").strip().lower() == "variable" and parent_sku:
            selected_rows.extend(
                row
                for row in rows
                if str(row.get("Type") or "").strip().lower() == "variation"
                and str(row.get("Parent") or "").strip() == parent_sku
            )
        segment_csv = _rows_to_csv_text(headers, selected_rows)
        products.append(parse_woocommerce_csv(segment_csv))
    _patch_batch_provenance(products, detected_product_count=len(product_rows))
    return products


def parse_bigcommerce_csv_batch(csv_text: str, *, source_weight_unit: str) -> list[Product]:
    headers, rows = csv_rows(csv_text)
    header_set = set(headers)
    if {"Item", "SKU", "Name"}.issubset(header_set):
        # Modern format: segment from each Product row to the next.
        product_indices = [
            index
            for index, row in enumerate(rows)
            if str(row.get("Item") or "").strip().lower() == "product"
        ]
        if not product_indices:
            raise ValueError("BigCommerce modern CSV requires at least one Product row.")
        products: list[Product] = []
        for idx, start in enumerate(product_indices):
            end = product_indices[idx + 1] if idx + 1 < len(product_indices) else len(rows)
            segment_csv = _rows_to_csv_text(headers, rows[start:end])
            products.append(
                parse_bigcommerce_csv(segment_csv, source_weight_unit=source_weight_unit)
            )
        _patch_batch_provenance(products, detected_product_count=len(product_indices))
        return products

    if {"Product Type", "Code", "Name"}.issubset(header_set):
        # Legacy format: one row per product.
        products: list[Product] = []
        for row in rows:
            segment_csv = _rows_to_csv_text(headers, [row])
            products.append(
                parse_bigcommerce_csv(segment_csv, source_weight_unit=source_weight_unit)
            )
        _patch_batch_provenance(products, detected_product_count=len(rows))
        return products

    raise ValueError("Unable to detect BigCommerce CSV format from headers.")


__all__ = [
    "import_products_from_csv",
]
