
import csv
import io

from ...canonical import Identifiers, Inventory, Product, Seo, SourceRef, Variant
from ...exporters.platforms.shopify import SHOPIFY_COLUMNS

from .bigcommerce import parse_bigcommerce_csv
from .common import (
    MAX_CSV_UPLOAD_BYTES,
    add_csv_provenance,
    apply_extra_product_fields,
    apply_extra_variant_fields,
    csv_rows,
    decode_csv_bytes,
    media_from_urls,
    option_defs_from_option_maps,
    parse_bool,
    parse_float,
    parse_int,
    price_from_amount,
    require_headers,
    split_tokens,
    taxonomy_from_primary,
    weight_object,
)
from .squarespace import parse_squarespace_csv
from .wix import parse_wix_csv
from .woocommerce import parse_woocommerce_csv


_SHOPIFY_REQUIRED_HEADERS = ("Handle", "Title", "Body (HTML)", "Variant SKU", "Variant Price")


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
    if len(csv_bytes) > MAX_CSV_UPLOAD_BYTES:
        raise ValueError("CSV file exceeds 5 MB limit.")

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
    require_headers(headers, _SHOPIFY_REQUIRED_HEADERS)

    handles: list[str] = []
    for row in rows:
        handle = str(row.get("Handle") or "").strip()
        if not handle:
            continue
        if handle not in handles:
            handles.append(handle)
    if not handles:
        raise ValueError("Shopify CSV must include at least one row with Handle.")

    products: list[Product] = []
    known_headers = set(SHOPIFY_COLUMNS)

    for selected_handle in handles:
        selected_rows = [
            row for row in rows if str(row.get("Handle") or "").strip() == selected_handle
        ]
        if not selected_rows:
            continue
        product_row = selected_rows[0]

        product_images: list[str] = []
        variants: list[Variant] = []
        option_maps: list[dict[str, str]] = []

        for index, row in enumerate(selected_rows, start=1):
            image_src = str(row.get("Image Src") or "").strip()
            if image_src and image_src not in product_images:
                product_images.append(image_src)

            sku = str(row.get("Variant SKU") or "").strip()
            if not sku:
                continue

            option_map: dict[str, str] = {}
            for option_index in range(1, 4):
                option_name = str(row.get(f"Option{option_index} Name") or "").strip()
                option_value = str(row.get(f"Option{option_index} Value") or "").strip()
                if option_name and option_value:
                    option_map[option_name] = option_value
            option_maps.append(option_map)

            quantity = parse_int(row.get("Variant Inventory Qty"))
            weight_grams = parse_float(row.get("Variant Grams"))
            variant_image = str(row.get("Variant Image") or "").strip()
            variant = Variant(
                id=str(index),
                sku=sku,
                title=" / ".join(option_map.values()) or None,
                option_values=[{"name": key, "value": value} for key, value in option_map.items()],
                price=price_from_amount(parse_float(row.get("Variant Price"))),
                inventory=Inventory(
                    track_quantity=(quantity is not None),
                    quantity=quantity,
                    available=(quantity > 0 if quantity is not None else True),
                ),
                weight=weight_object(weight_grams),
                media=media_from_urls([variant_image], variant_sku=sku),
                identifiers=Identifiers(values={"source_variant_id": str(index), "sku": sku}),
            )
            apply_extra_variant_fields(variant, row, known_headers=known_headers)
            variants.append(variant)

        if not variants:
            raise ValueError("Shopify CSV must include at least one variant row with Variant SKU.")

        requires_shipping_value = parse_bool(product_row.get("Variant Requires Shipping"))
        requires_shipping = True if requires_shipping_value is None else requires_shipping_value
        product = Product(
            source=SourceRef(platform="shopify", id=selected_handle, slug=selected_handle, url=None),
            title=str(product_row.get("Title") or "").strip() or None,
            description=str(product_row.get("Body (HTML)") or "").strip() or None,
            seo=Seo(
                title=str(product_row.get("Title") or "").strip() or None,
                description=str(product_row.get("Body (HTML)") or "").strip() or None,
            ),
            vendor=str(product_row.get("Vendor") or "").strip() or None,
            brand=str(product_row.get("Vendor") or "").strip() or None,
            taxonomy=taxonomy_from_primary(str(product_row.get("Type") or "").strip() or None),
            tags=split_tokens(product_row.get("Tags"), sep=","),
            options=option_defs_from_option_maps(option_maps),
            variants=variants,
            price=variants[0].price,
            weight=variants[0].weight,
            requires_shipping=requires_shipping,
            track_quantity=any(variant.inventory.track_quantity for variant in variants),
            is_digital=not requires_shipping,
            media=media_from_urls(product_images),
            identifiers=Identifiers(values={"source_product_id": selected_handle, "handle": selected_handle}),
        )
        apply_extra_product_fields(product, product_row, known_headers=known_headers)
        add_csv_provenance(
            product,
            source_platform=source_platform,
            detected_product_count=len(handles),
            selected_product_key=selected_handle,
        )
        products.append(product)

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
        row
        for row in rows
        if str(row.get("Type") or "").strip().lower() in {"simple", "variable"}
    ]
    if not product_rows:
        raise ValueError("WooCommerce CSV must include at least one simple or variable product row.")

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
            products.append(parse_bigcommerce_csv(segment_csv, source_weight_unit=source_weight_unit))
        _patch_batch_provenance(products, detected_product_count=len(product_indices))
        return products

    if {"Product Type", "Code", "Name"}.issubset(header_set):
        # Legacy format: one row per product.
        products: list[Product] = []
        for row in rows:
            segment_csv = _rows_to_csv_text(headers, [row])
            products.append(parse_bigcommerce_csv(segment_csv, source_weight_unit=source_weight_unit))
        _patch_batch_provenance(products, detected_product_count=len(rows))
        return products

    raise ValueError("Unable to detect BigCommerce CSV format from headers.")


__all__ = [
    "import_products_from_csv",
    "parse_shopify_csv_batch",
    "parse_bigcommerce_csv_batch",
    "parse_wix_csv_batch",
    "parse_squarespace_csv_batch",
    "parse_woocommerce_csv_batch",
]
