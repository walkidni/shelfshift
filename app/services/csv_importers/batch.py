from __future__ import annotations

from app.models import Identifiers, Inventory, Product, Seo, SourceRef, Variant
from app.services.exporters.shopify_csv import SHOPIFY_COLUMNS

from .common import (
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


_SHOPIFY_REQUIRED_HEADERS = ("Handle", "Title", "Body (HTML)", "Variant SKU", "Variant Price")


def import_products_from_csv(
    *,
    source_platform: str,
    csv_bytes: bytes,
    source_weight_unit: str | None = None,
) -> list[Product]:
    platform = str(source_platform or "").strip().lower()
    if platform != "shopify":
        raise ValueError(f"Batch CSV import is not implemented for source_platform={platform}.")
    if not csv_bytes:
        raise ValueError("CSV file is empty.")

    csv_text = decode_csv_bytes(csv_bytes)
    return parse_shopify_csv_batch(csv_text, source_platform=platform)


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

    return products


__all__ = [
    "import_products_from_csv",
    "parse_shopify_csv_batch",
]

