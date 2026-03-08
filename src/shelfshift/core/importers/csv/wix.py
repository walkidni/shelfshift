from ...canonical import Inventory, Product, Seo, SourceRef, Variant
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
    require_headers,
    split_tokens,
    unmapped_headers_from_csv,
    weight_object,
    weight_to_grams,
)

_REQUIRED_HEADERS = ("handle", "fieldType", "name", "price", "sku")
_WIX_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "handle": ("handle",),
    "name": ("name",),
    "visible": ("visible",),
    "plain_description": ("plainDescription",),
    "media": ("media",),
    "brand": ("brand",),
    "price": ("price",),
    "inventory": ("inventory",),
    "sku": ("sku",),
    "weight": ("weight",),
}
_WIX_OPTION_NAME_TEMPLATE = "productOptionName{i}"
_WIX_OPTION_CHOICES_TEMPLATE = "productOptionChoices{i}"
_WIX_CANONICAL_MAPPED_HEADERS: set[str] = infer_mapped_headers(
    alias_maps=[_WIX_HEADER_ALIASES],
    indexed_header_families=[
        ((_WIX_OPTION_NAME_TEMPLATE, _WIX_OPTION_CHOICES_TEMPLATE), range(1, 7))
    ],
)


def _variant_inventory_from_wix(value: str) -> Inventory:
    quantity = parse_int(value)
    if quantity is not None:
        return Inventory(track_quantity=True, quantity=quantity, available=quantity > 0)
    lowered = str(value or "").strip().upper()
    if lowered == "IN_STOCK":
        return Inventory(track_quantity=False, quantity=None, available=True)
    if lowered == "OUT_OF_STOCK":
        return Inventory(track_quantity=False, quantity=None, available=False)
    return Inventory(track_quantity=False, quantity=None, available=True)


def _first_non_empty(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _field_value(row: dict[str, str], field: str) -> str:
    return _first_non_empty(row, *_WIX_HEADER_ALIASES[field])


def parse_wix_csv(csv_text: str, *, source_weight_unit: str) -> Product:
    headers, rows = csv_rows(csv_text)
    require_headers(headers, _REQUIRED_HEADERS)
    unmapped_headers = unmapped_headers_from_csv(
        headers,
        mapped_headers=_WIX_CANONICAL_MAPPED_HEADERS,
    )
    handles: list[str] = []
    selected_handle = ""
    for row in rows:
        handle = _field_value(row, "handle")
        if not handle:
            continue
        if handle not in handles:
            handles.append(handle)
        if not selected_handle:
            selected_handle = handle
    if not selected_handle:
        raise ValueError("Wix CSV must include at least one row with handle.")

    selected_rows = [row for row in rows if _field_value(row, "handle") == selected_handle]
    product_rows = [
        row for row in selected_rows if str(row.get("fieldType") or "").strip().upper() == "PRODUCT"
    ]
    product_row = product_rows[0] if product_rows else selected_rows[0]
    variant_rows = [
        row for row in selected_rows if str(row.get("fieldType") or "").strip().upper() == "VARIANT"
    ]
    media_rows = [
        row for row in selected_rows if str(row.get("fieldType") or "").strip().upper() == "MEDIA"
    ]

    option_maps: list[dict[str, str]] = []
    variants: list[Variant] = []
    source_rows = variant_rows or [product_row]
    for index, row in enumerate(source_rows, start=1):
        sku = _field_value(row, "sku") or f"{selected_handle}:{index}"
        option_map: dict[str, str] = {}
        for option_index in range(1, 7):
            name = str(
                row.get(_WIX_OPTION_NAME_TEMPLATE.replace("{i}", str(option_index))) or ""
            ).strip()
            value = str(
                row.get(_WIX_OPTION_CHOICES_TEMPLATE.replace("{i}", str(option_index))) or ""
            ).strip()
            if name and value:
                selected = split_tokens(value, sep=";")
                option_map[name] = selected[0] if selected else value
        option_maps.append(option_map)

        weight_grams = weight_to_grams(
            _field_value(row, "weight"), source_weight_unit=source_weight_unit
        )
        variant = Variant(
            id=str(index),
            sku=sku,
            title=" / ".join(option_map.values()) or None,
            option_values=[{"name": key, "value": value} for key, value in option_map.items()],
            price=price_from_amount(parse_float(_field_value(row, "price"))),
            inventory=_variant_inventory_from_wix(_field_value(row, "inventory")),
            weight=weight_object(weight_grams),
            media=media_from_urls([_field_value(row, "media")], variant_sku=sku),
            identifiers=make_identifiers({"source_variant_id": str(index), "sku": sku}),
        )
        variants.append(variant)

    media_urls: list[str] = []
    product_media = _field_value(product_row, "media")
    if product_media:
        media_urls.append(product_media)
    for row in media_rows:
        url = _field_value(row, "media")
        if url:
            media_urls.append(url)

    product = Product(
        source=SourceRef(platform="wix", id=None, slug=selected_handle, url=None),
        title=_field_value(product_row, "name") or None,
        description=_field_value(product_row, "plain_description") or None,
        seo=Seo(
            title=_field_value(product_row, "name") or None,
            description=_field_value(product_row, "plain_description") or None,
        ),
        brand=_field_value(product_row, "brand") or None,
        vendor=_field_value(product_row, "brand") or None,
        variants=variants,
        options=option_defs_from_option_maps(option_maps),
        price=price_from_amount(parse_float(_field_value(product_row, "price"))),
        weight=variants[0].weight,
        requires_shipping=True,
        track_quantity=any(variant.inventory.track_quantity for variant in variants),
        is_digital=False,
        is_published=parse_bool(_field_value(product_row, "visible")),
        media=media_from_urls(media_urls),
        identifiers=make_identifiers({"source_product_id": selected_handle}),
    )
    apply_first_non_empty_unmapped_fields(
        product.unmapped_fields,
        platform="wix",
        rows=[product_row],
        headers=unmapped_headers,
    )
    for variant, row in zip(variants, source_rows, strict=False):
        apply_row_unmapped_fields(
            variant.unmapped_fields,
            platform="wix",
            row=row,
            headers=unmapped_headers,
        )
    add_csv_provenance(
        product,
        source_platform="wix",
        detected_product_count=len(handles),
        selected_product_key=selected_handle,
    )
    return product
