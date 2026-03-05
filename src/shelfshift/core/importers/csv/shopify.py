from ...canonical import Inventory, Product, Seo, SourceRef, Variant
from ...exporters.platforms.shopify import SHOPIFY_COLUMNS
from ..unmapped_fields import platform_unmapped_key, set_unmapped_field
from .common import (
    add_csv_provenance,
    apply_extra_product_fields,
    apply_extra_variant_fields,
    csv_rows,
    make_identifiers,
    media_from_urls,
    option_defs_from_option_maps,
    parse_bool,
    parse_float,
    parse_int,
    price_from_amount,
    split_tokens,
    taxonomy_from_primary,
    weight_object,
)

SHOPIFY_REQUIRED_HEADERS_OLD = (
    "Handle",
    "Title",
    "Body (HTML)",
    "Variant SKU",
    "Variant Price",
)
SHOPIFY_REQUIRED_HEADERS_NEW = ("URL handle", "Title", "Description", "SKU", "Price")

SHOPIFY_LEGACY_COLUMNS = {
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Type",
    "Tags",
    "Published",
    "Status",
    "Option1 Name",
    "Option1 Value",
    "Option2 Name",
    "Option2 Value",
    "Option3 Name",
    "Option3 Value",
    "Variant SKU",
    "Variant Grams",
    "Variant Inventory Tracker",
    "Variant Inventory Qty",
    "Variant Inventory Policy",
    "Variant Fulfillment Service",
    "Variant Price",
    "Variant Requires Shipping",
    "Variant Taxable",
    "Image Src",
    "Image Position",
    "Image Alt Text",
    "Variant Image",
    "Variant Weight Unit",
}


def _first_non_empty(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _shopify_has_required_headers(headers: list[str], required_headers: tuple[str, ...]) -> bool:
    return set(required_headers).issubset(set(headers))


def require_shopify_headers(headers: list[str]) -> None:
    if _shopify_has_required_headers(headers, SHOPIFY_REQUIRED_HEADERS_OLD):
        return
    if _shopify_has_required_headers(headers, SHOPIFY_REQUIRED_HEADERS_NEW):
        return
    raise ValueError(
        "Missing required Shopify CSV headers. Expected either legacy headers "
        "(Handle, Title, Body (HTML), Variant SKU, Variant Price) or new headers "
        "(URL handle, Title, Description, SKU, Price)."
    )


def shopify_row_handle(row: dict[str, str]) -> str:
    return _first_non_empty(row, "Handle", "URL handle")


def extract_shopify_handles(rows: list[dict[str, str]]) -> list[str]:
    handles: list[str] = []
    for row in rows:
        handle = shopify_row_handle(row)
        if not handle:
            continue
        if handle not in handles:
            handles.append(handle)
    return handles


def parse_shopify_csv(csv_text: str, *, source_platform: str = "shopify") -> Product:
    headers, rows = csv_rows(csv_text)
    require_shopify_headers(headers)

    handles = extract_shopify_handles(rows)
    if not handles:
        raise ValueError("Shopify CSV must include at least one row with Handle or URL handle.")

    selected_handle = handles[0]
    selected_rows = [row for row in rows if shopify_row_handle(row) == selected_handle]
    product_row = selected_rows[0]
    known_headers = set(SHOPIFY_COLUMNS) | SHOPIFY_LEGACY_COLUMNS

    product_images: list[str] = []
    variants: list[Variant] = []
    option_maps: list[dict[str, str]] = []

    for index, row in enumerate(selected_rows, start=1):
        image_src = _first_non_empty(row, "Image Src", "Product image URL")
        if image_src and image_src not in product_images:
            product_images.append(image_src)

        sku = _first_non_empty(row, "Variant SKU", "SKU")
        if not sku:
            continue

        option_map: dict[str, str] = {}
        for option_index in range(1, 4):
            option_name = _first_non_empty(
                row, f"Option{option_index} Name", f"Option{option_index} name"
            )
            option_value = _first_non_empty(
                row, f"Option{option_index} Value", f"Option{option_index} value"
            )
            if option_name and option_value:
                option_map[option_name] = option_value
        option_maps.append(option_map)

        quantity = parse_int(_first_non_empty(row, "Variant Inventory Qty", "Inventory quantity"))
        weight_grams = parse_float(_first_non_empty(row, "Variant Grams", "Weight value (grams)"))
        variant_image = _first_non_empty(row, "Variant Image", "Variant image URL")
        variant = Variant(
            id=str(index),
            sku=sku,
            title=" / ".join(option_map.values()) or None,
            option_values=[{"name": key, "value": value} for key, value in option_map.items()],
            price=price_from_amount(parse_float(_first_non_empty(row, "Variant Price", "Price"))),
            inventory=Inventory(
                track_quantity=(quantity is not None),
                quantity=quantity,
                available=(quantity > 0 if quantity is not None else True),
            ),
            weight=weight_object(weight_grams),
            media=media_from_urls([variant_image], variant_sku=sku),
            identifiers=make_identifiers({"source_variant_id": str(index), "sku": sku}),
        )
        apply_extra_variant_fields(
            variant,
            row,
            known_headers=known_headers,
            source_platform=source_platform,
        )
        variants.append(variant)

    if not variants:
        raise ValueError(
            "Shopify CSV must include at least one variant row with Variant SKU or SKU."
        )

    requires_shipping_value = parse_bool(
        _first_non_empty(product_row, "Variant Requires Shipping", "Requires shipping")
    )
    requires_shipping = True if requires_shipping_value is None else requires_shipping_value
    visibility = parse_bool(_first_non_empty(product_row, "Published on online store", "Published"))
    if visibility is None:
        status = _first_non_empty(product_row, "Status").strip().lower()
        if status == "active":
            visibility = True
        elif status in {"draft", "archived"}:
            visibility = False

    product = Product(
        source=SourceRef(platform="shopify", id=None, slug=selected_handle, url=None),
        title=_first_non_empty(product_row, "Title") or None,
        description=_first_non_empty(product_row, "Body (HTML)", "Description") or None,
        seo=Seo(
            title=_first_non_empty(product_row, "Title") or None,
            description=_first_non_empty(product_row, "Body (HTML)", "Description") or None,
        ),
        vendor=_first_non_empty(product_row, "Vendor") or None,
        brand=_first_non_empty(product_row, "Vendor") or None,
        taxonomy=taxonomy_from_primary(_first_non_empty(product_row, "Product category") or None),
        tags=split_tokens(product_row.get("Tags"), sep=","),
        options=option_defs_from_option_maps(option_maps),
        variants=variants,
        price=variants[0].price,
        weight=variants[0].weight,
        requires_shipping=requires_shipping,
        track_quantity=any(variant.inventory.track_quantity for variant in variants),
        is_digital=not requires_shipping,
        visibility=visibility,
        media=media_from_urls(product_images),
        identifiers=make_identifiers(values={"source_product_id": selected_handle}),
    )
    set_unmapped_field(
        product.unmapped_fields,
        key=platform_unmapped_key(source_platform, "type"),
        value=_first_non_empty(product_row, "Type"),
    )
    apply_extra_product_fields(
        product,
        product_row,
        known_headers=known_headers,
        source_platform=source_platform,
    )
    add_csv_provenance(
        product,
        source_platform=source_platform,
        detected_product_count=len(handles),
        selected_product_key=selected_handle,
    )
    return product


__all__ = [
    "extract_shopify_handles",
    "parse_shopify_csv",
    "require_shopify_headers",
    "shopify_row_handle",
]
