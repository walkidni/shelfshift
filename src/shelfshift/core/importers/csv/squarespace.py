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
    split_image_lines,
    split_tokens,
    taxonomy_from_primary,
    unmapped_headers_from_csv,
    weight_object,
    weight_to_grams,
)

_REQUIRED_HEADERS = ("Title", "SKU", "Price", "Product Type [Non Editable]", "Visible")
_SQUARESPACE_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "product_id": ("Product ID [Non Editable]",),
    "variant_id": ("Variant ID [Non Editable]",),
    "product_type": ("Product Type [Non Editable]",),
    "product_url": ("Product URL",),
    "title": ("Title",),
    "description": ("Description",),
    "sku": ("SKU",),
    "price": ("Price",),
    "stock": ("Stock",),
    "categories": ("Categories",),
    "tags": ("Tags",),
    "weight": ("Weight",),
    "visible": ("Visible",),
    "hosted_image_urls": ("Hosted Image URLs",),
}
_SQUARESPACE_OPTION_NAME_TEMPLATE = "Option Name {i}"
_SQUARESPACE_OPTION_VALUE_TEMPLATE = "Option Value {i}"
_SQUARESPACE_CANONICAL_MAPPED_HEADERS: set[str] = infer_mapped_headers(
    alias_maps=[_SQUARESPACE_HEADER_ALIASES],
    indexed_header_families=[
        ((_SQUARESPACE_OPTION_NAME_TEMPLATE, _SQUARESPACE_OPTION_VALUE_TEMPLATE), range(1, 7))
    ],
)


def _segment_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    anchors = [index for index, row in enumerate(rows) if _field_value(row, "title")]
    if not anchors:
        return rows, 1
    start = anchors[0]
    end = anchors[1] if len(anchors) > 1 else len(rows)
    return rows[start:end], len(anchors)


def _first_non_empty(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _field_value(row: dict[str, str], field: str) -> str:
    return _first_non_empty(row, *_SQUARESPACE_HEADER_ALIASES[field])


def parse_squarespace_csv(csv_text: str, *, source_weight_unit: str) -> Product:
    headers, rows = csv_rows(csv_text)
    require_headers(headers, _REQUIRED_HEADERS)
    unmapped_headers = unmapped_headers_from_csv(
        headers,
        mapped_headers=_SQUARESPACE_CANONICAL_MAPPED_HEADERS,
    )
    selected_rows, detected_product_count = _segment_rows(rows)
    product_row = selected_rows[0]

    variants: list[Variant] = []
    option_maps: list[dict[str, str]] = []
    variant_source_rows: list[dict[str, str]] = []
    for index, row in enumerate(selected_rows, start=1):
        sku = _field_value(row, "sku")
        if not sku:
            continue
        variant_source_rows.append(row)
        option_map: dict[str, str] = {}
        for option_index in range(1, 7):
            name = str(
                row.get(_SQUARESPACE_OPTION_NAME_TEMPLATE.replace("{i}", str(option_index))) or ""
            ).strip()
            value = str(
                row.get(_SQUARESPACE_OPTION_VALUE_TEMPLATE.replace("{i}", str(option_index))) or ""
            ).strip()
            if name and value:
                option_map[name] = value
        option_maps.append(option_map)

        stock_raw = _field_value(row, "stock")
        quantity = None if stock_raw.lower() == "unlimited" else parse_int(stock_raw)
        track_quantity = stock_raw.lower() != "unlimited"
        weight_grams = weight_to_grams(
            _field_value(row, "weight"),
            source_weight_unit=source_weight_unit,
        )
        variant = Variant(
            id=str(index),
            sku=sku,
            title=" / ".join(option_map.values()) or None,
            option_values=[{"name": key, "value": value} for key, value in option_map.items()],
            price=price_from_amount(parse_float(row.get("Price"))),
            inventory=Inventory(
                track_quantity=track_quantity,
                quantity=quantity,
                available=(quantity > 0 if quantity is not None else True),
            ),
            weight=weight_object(weight_grams),
            identifiers=make_identifiers(
                {
                    "source_variant_id": _field_value(row, "variant_id") or str(index),
                    "sku": sku,
                }
            ),
        )
        variants.append(variant)

    if not variants:
        raise ValueError("Squarespace CSV must include at least one row with SKU.")

    product_url = _field_value(product_row, "product_url")
    slug = product_url.strip("/").split("/")[-1] if product_url else None
    product_type = _field_value(product_row, "product_type").upper()
    is_digital = product_type == "DIGITAL"
    media_urls = split_image_lines(_field_value(product_row, "hosted_image_urls"))
    source_id = _field_value(product_row, "product_id") or None
    product = Product(
        source=SourceRef(platform="squarespace", id=source_id, slug=slug, url=product_url or None),
        title=_field_value(product_row, "title") or None,
        description=_field_value(product_row, "description") or None,
        seo=Seo(
            title=_field_value(product_row, "title") or None,
            description=_field_value(product_row, "description") or None,
        ),
        tags=split_tokens(_field_value(product_row, "tags"), sep=","),
        taxonomy=taxonomy_from_primary(_field_value(product_row, "categories") or None),
        variants=variants,
        options=option_defs_from_option_maps(option_maps),
        price=price_from_amount(parse_float(_field_value(product_row, "price"))),
        weight=variants[0].weight,
        requires_shipping=not is_digital,
        track_quantity=any(variant.inventory.track_quantity for variant in variants),
        is_digital=is_digital,
        is_published=parse_bool(_field_value(product_row, "visible")),
        media=media_from_urls(media_urls),
        identifiers=make_identifiers({"source_product_id": slug or variants[0].sku}),
    )
    apply_first_non_empty_unmapped_fields(
        product.unmapped_fields,
        platform="squarespace",
        rows=[product_row],
        headers=unmapped_headers,
    )
    for variant, row in zip(variants, variant_source_rows, strict=False):
        apply_row_unmapped_fields(
            variant.unmapped_fields,
            platform="squarespace",
            row=row,
            headers=unmapped_headers,
        )
    add_csv_provenance(
        product,
        source_platform="squarespace",
        detected_product_count=detected_product_count,
        selected_product_key=slug or _field_value(product_row, "title") or variants[0].sku,
    )
    return product
