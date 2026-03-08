from ...canonical import Inventory, Product, Seo, SourceRef, Variant
from ...csv_schemas.shopify import (
    SHOPIFY_HEADER_ALIASES,
    SHOPIFY_OPTION_NAME_TEMPLATES,
    SHOPIFY_OPTION_VALUE_TEMPLATES,
    SHOPIFY_REQUIRED_HEADERS_NEW,
    SHOPIFY_REQUIRED_HEADERS_OLD,
)
from .common import (
    add_csv_provenance,
    apply_first_non_empty_unmapped_fields,
    apply_row_unmapped_fields,
    csv_rows,
    infer_mapped_headers,
    make_identifiers,
    media_from_urls,
    option_defs_from_option_maps,
    parse_bool,
    parse_float,
    parse_int,
    price_from_amount,
    split_tokens,
    taxonomy_from_primary,
    unmapped_headers_from_csv,
    weight_object,
)

_SHOPIFY_CANONICAL_MAPPED_HEADERS: set[str] = infer_mapped_headers(
    alias_maps=[SHOPIFY_HEADER_ALIASES],
    indexed_header_families=[
        (SHOPIFY_OPTION_NAME_TEMPLATES, range(1, 4)),
        (SHOPIFY_OPTION_VALUE_TEMPLATES, range(1, 4)),
    ],
)


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
    return _first_non_empty(row, *SHOPIFY_HEADER_ALIASES["handle"])


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
    unmapped_headers = unmapped_headers_from_csv(
        headers,
        mapped_headers=_SHOPIFY_CANONICAL_MAPPED_HEADERS,
    )

    handles = extract_shopify_handles(rows)
    if not handles:
        raise ValueError("Shopify CSV must include at least one row with Handle or URL handle.")

    selected_handle = handles[0]
    selected_rows = [row for row in rows if shopify_row_handle(row) == selected_handle]
    product_row = selected_rows[0]
    product_images: list[str] = []
    variants: list[Variant] = []
    option_maps: list[dict[str, str]] = []
    variant_source_rows: list[dict[str, str]] = []

    for index, row in enumerate(selected_rows, start=1):
        image_src = _first_non_empty(row, *SHOPIFY_HEADER_ALIASES["product_image"])
        if image_src and image_src not in product_images:
            product_images.append(image_src)

        sku = _first_non_empty(row, *SHOPIFY_HEADER_ALIASES["variant_sku"])
        if not sku:
            continue
        variant_source_rows.append(row)

        option_map: dict[str, str] = {}
        for option_index in range(1, 4):
            option_name = _first_non_empty(
                row,
                *(
                    template.replace("{i}", str(option_index))
                    for template in SHOPIFY_OPTION_NAME_TEMPLATES
                ),
            )
            option_value = _first_non_empty(
                row,
                *(
                    template.replace("{i}", str(option_index))
                    for template in SHOPIFY_OPTION_VALUE_TEMPLATES
                ),
            )
            if option_name and option_value:
                option_map[option_name] = option_value
        option_maps.append(option_map)

        quantity = parse_int(
            _first_non_empty(row, *SHOPIFY_HEADER_ALIASES["variant_inventory_qty"])
        )
        weight_grams = parse_float(
            _first_non_empty(row, *SHOPIFY_HEADER_ALIASES["variant_weight_grams"])
        )
        variant_image = _first_non_empty(row, *SHOPIFY_HEADER_ALIASES["variant_image"])
        variant = Variant(
            id=str(index),
            sku=sku,
            title=" / ".join(option_map.values()) or None,
            option_values=[{"name": key, "value": value} for key, value in option_map.items()],
            price=price_from_amount(
                parse_float(_first_non_empty(row, *SHOPIFY_HEADER_ALIASES["variant_price"]))
            ),
            inventory=Inventory(
                track_quantity=(quantity is not None),
                quantity=quantity,
                available=(quantity > 0 if quantity is not None else True),
            ),
            weight=weight_object(weight_grams),
            media=media_from_urls([variant_image], variant_sku=sku),
            identifiers=make_identifiers({"source_variant_id": str(index), "sku": sku}),
        )
        variants.append(variant)

    if not variants:
        raise ValueError(
            "Shopify CSV must include at least one variant row with Variant SKU or SKU."
        )

    requires_shipping_value = parse_bool(
        _first_non_empty(product_row, *SHOPIFY_HEADER_ALIASES["requires_shipping"])
    )
    requires_shipping = True if requires_shipping_value is None else requires_shipping_value
    publish_header = (
        "Published"
        if _shopify_has_required_headers(headers, SHOPIFY_REQUIRED_HEADERS_OLD)
        else "Published on online store"
    )
    is_published = parse_bool(product_row.get(publish_header))

    product = Product(
        source=SourceRef(platform="shopify", id=None, slug=selected_handle, url=None),
        title=_first_non_empty(product_row, *SHOPIFY_HEADER_ALIASES["title"]) or None,
        description=_first_non_empty(product_row, *SHOPIFY_HEADER_ALIASES["description"]) or None,
        seo=Seo(
            title=_first_non_empty(product_row, *SHOPIFY_HEADER_ALIASES["title"]) or None,
            description=_first_non_empty(product_row, *SHOPIFY_HEADER_ALIASES["description"])
            or None,
        ),
        vendor=_first_non_empty(product_row, *SHOPIFY_HEADER_ALIASES["vendor"]) or None,
        brand=_first_non_empty(product_row, *SHOPIFY_HEADER_ALIASES["vendor"]) or None,
        taxonomy=taxonomy_from_primary(
            _first_non_empty(product_row, *SHOPIFY_HEADER_ALIASES["product_category"]) or None
        ),
        tags=split_tokens(_first_non_empty(product_row, *SHOPIFY_HEADER_ALIASES["tags"]), sep=","),
        options=option_defs_from_option_maps(option_maps),
        variants=variants,
        price=variants[0].price,
        weight=variants[0].weight,
        requires_shipping=requires_shipping,
        track_quantity=any(variant.inventory.track_quantity for variant in variants),
        is_digital=not requires_shipping,
        is_published=is_published,
        media=media_from_urls(product_images),
        identifiers=make_identifiers(values={"source_product_id": selected_handle}),
    )
    apply_first_non_empty_unmapped_fields(
        product.unmapped_fields,
        platform=source_platform,
        rows=[product_row],
        headers=unmapped_headers,
    )
    for variant, row in zip(variants, variant_source_rows, strict=False):
        apply_row_unmapped_fields(
            variant.unmapped_fields,
            platform=source_platform,
            row=row,
            headers=unmapped_headers,
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
