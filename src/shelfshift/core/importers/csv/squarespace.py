from ...canonical import Inventory, Product, Seo, SourceRef, Variant
from .common import (
    add_csv_provenance,
    apply_first_non_empty_unmapped_fields,
    apply_row_unmapped_fields,
    csv_rows,
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
_SQUARESPACE_CANONICAL_MAPPED_HEADERS: set[str] = {
    "Product ID [Non Editable]",
    "Variant ID [Non Editable]",
    "Product Type [Non Editable]",
    "Product URL",
    "Title",
    "Description",
    "SKU",
    "Option Name 1",
    "Option Value 1",
    "Option Name 2",
    "Option Value 2",
    "Option Name 3",
    "Option Value 3",
    "Price",
    "Stock",
    "Categories",
    "Tags",
    "Weight",
    "Visible",
    "Hosted Image URLs",
}


def _segment_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    anchors = [index for index, row in enumerate(rows) if str(row.get("Title") or "").strip()]
    if not anchors:
        return rows, 1
    start = anchors[0]
    end = anchors[1] if len(anchors) > 1 else len(rows)
    return rows[start:end], len(anchors)


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
        sku = str(row.get("SKU") or "").strip()
        if not sku:
            continue
        variant_source_rows.append(row)
        option_map: dict[str, str] = {}
        for option_index in range(1, 4):
            name = str(row.get(f"Option Name {option_index}") or "").strip()
            value = str(row.get(f"Option Value {option_index}") or "").strip()
            if name and value:
                option_map[name] = value
        option_maps.append(option_map)

        stock_raw = str(row.get("Stock") or "").strip()
        quantity = None if stock_raw.lower() == "unlimited" else parse_int(stock_raw)
        track_quantity = stock_raw.lower() != "unlimited"
        weight_grams = weight_to_grams(row.get("Weight"), source_weight_unit=source_weight_unit)
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
                    "source_variant_id": str(row.get("Variant ID [Non Editable]") or "").strip()
                    or str(index),
                    "sku": sku,
                }
            ),
        )
        variants.append(variant)

    if not variants:
        raise ValueError("Squarespace CSV must include at least one row with SKU.")

    product_url = str(product_row.get("Product URL") or "").strip()
    slug = product_url.strip("/").split("/")[-1] if product_url else None
    product_type = str(product_row.get("Product Type [Non Editable]") or "").strip().upper()
    is_digital = product_type == "DIGITAL"
    media_urls = split_image_lines(product_row.get("Hosted Image URLs"))
    source_id = str(product_row.get("Product ID [Non Editable]") or "").strip() or None
    product = Product(
        source=SourceRef(platform="squarespace", id=source_id, slug=slug, url=product_url or None),
        title=str(product_row.get("Title") or "").strip() or None,
        description=str(product_row.get("Description") or "").strip() or None,
        seo=Seo(
            title=str(product_row.get("Title") or "").strip() or None,
            description=str(product_row.get("Description") or "").strip() or None,
        ),
        tags=split_tokens(product_row.get("Tags"), sep=","),
        taxonomy=taxonomy_from_primary(str(product_row.get("Categories") or "").strip() or None),
        variants=variants,
        options=option_defs_from_option_maps(option_maps),
        price=price_from_amount(parse_float(product_row.get("Price"))),
        weight=variants[0].weight,
        requires_shipping=not is_digital,
        track_quantity=any(variant.inventory.track_quantity for variant in variants),
        is_digital=is_digital,
        is_published=parse_bool(product_row.get("Visible")),
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
        selected_product_key=slug or str(product_row.get("Title") or "").strip() or variants[0].sku,
    )
    return product
