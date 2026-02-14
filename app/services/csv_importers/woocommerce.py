from slugify import slugify

from app.models import CategorySet, Identifiers, Inventory, Product, Seo, SourceRef, Variant
from app.services.exporters.woocommerce_csv import WOOCOMMERCE_COLUMNS

from .common import (
    add_csv_provenance,
    apply_extra_product_fields,
    apply_extra_variant_fields,
    csv_rows,
    media_from_urls,
    option_defs_from_option_maps,
    parse_bool,
    parse_float,
    parse_int,
    price_from_amount,
    require_headers,
    split_tokens,
    weight_object,
    weight_to_grams,
)


_REQUIRED_HEADERS = ("Type", "SKU", "Name", "Regular price")


def _taxonomy_from_categories(value: str) -> CategorySet:
    cleaned = str(value or "").strip()
    if not cleaned:
        return CategorySet()
    parts = [token.strip() for token in cleaned.split(">") if token.strip()]
    if not parts:
        return CategorySet()
    return CategorySet(paths=[parts], primary=list(parts))


def _row_option_map(row: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for index in range(1, 4):
        name = str(row.get(f"Attribute {index} name") or "").strip()
        value = str(row.get(f"Attribute {index} value(s)") or "").strip()
        if not name or not value:
            continue
        first_value = split_tokens(value, sep=",")
        if first_value:
            out[name] = first_value[0]
    return out


def parse_woocommerce_csv(csv_text: str) -> Product:
    headers, rows = csv_rows(csv_text)
    require_headers(headers, _REQUIRED_HEADERS)
    known_headers = set(WOOCOMMERCE_COLUMNS)

    product_rows = [row for row in rows if str(row.get("Type") or "").strip().lower() in {"simple", "variable"}]
    if not product_rows:
        raise ValueError("WooCommerce CSV must include at least one simple or variable product row.")

    product_row = product_rows[0]
    detected_product_count = len(product_rows)
    parent_sku = str(product_row.get("SKU") or "").strip()

    product_type = str(product_row.get("Type") or "").strip().lower()
    selected_rows: list[dict[str, str]] = [product_row]
    if product_type == "variable" and parent_sku:
        selected_rows.extend(
            row
            for row in rows
            if str(row.get("Type") or "").strip().lower() == "variation"
            and str(row.get("Parent") or "").strip() == parent_sku
        )

    variant_rows = [row for row in selected_rows if str(row.get("Type") or "").strip().lower() == "variation"]
    if not variant_rows:
        variant_rows = [product_row]

    option_maps: list[dict[str, str]] = []
    variants: list[Variant] = []
    for index, row in enumerate(variant_rows, start=1):
        sku = str(row.get("SKU") or "").strip() or f"{parent_sku}:{index}"
        option_map = _row_option_map(row)
        option_maps.append(option_map)
        quantity = parse_int(row.get("Stock"))
        in_stock = parse_bool(row.get("In stock?"))
        price = parse_float(row.get("Regular price"))
        weight_grams = weight_to_grams(row.get("Weight (kg)"), source_weight_unit="kg")
        image_urls = split_tokens(row.get("Images"), sep=",")
        variant = Variant(
            id=str(index),
            sku=sku,
            title=" / ".join(option_map.values()) or None,
            option_values=[{"name": key, "value": value} for key, value in option_map.items()],
            price=price_from_amount(price),
            inventory=Inventory(
                track_quantity=(quantity is not None),
                quantity=quantity,
                available=(quantity > 0 if quantity is not None else in_stock),
            ),
            weight=weight_object(weight_grams),
            media=media_from_urls(image_urls, variant_sku=sku),
            identifiers=Identifiers(values={"source_variant_id": str(index), "sku": sku}),
        )
        apply_extra_variant_fields(variant, row, known_headers=known_headers)
        variants.append(variant)

    product_name = str(product_row.get("Name") or "").strip()
    slug = slugify(product_name) if product_name else None
    product_images = split_tokens(product_row.get("Images"), sep=",")
    tax_status = str(product_row.get("Tax status") or "").strip().lower()
    is_digital = tax_status == "none"
    product = Product(
        source=SourceRef(platform="woocommerce", id=parent_sku or slug, slug=slug, url=None),
        title=product_name or None,
        description=str(product_row.get("Description") or "").strip() or None,
        seo=Seo(
            title=product_name or None,
            description=str(product_row.get("Short description") or "").strip() or None,
        ),
        tags=split_tokens(product_row.get("Tags"), sep=","),
        taxonomy=_taxonomy_from_categories(str(product_row.get("Categories") or "").strip()),
        options=option_defs_from_option_maps(option_maps),
        variants=variants,
        price=price_from_amount(parse_float(product_row.get("Regular price"))),
        weight=variants[0].weight,
        requires_shipping=not is_digital,
        track_quantity=any(variant.inventory.track_quantity for variant in variants),
        is_digital=is_digital,
        media=media_from_urls(product_images),
        identifiers=Identifiers(values={"source_product_id": parent_sku or slug or "woocommerce-product"}),
    )
    apply_extra_product_fields(product, product_row, known_headers=known_headers)
    add_csv_provenance(
        product,
        source_platform="woocommerce",
        detected_product_count=detected_product_count,
        selected_product_key=parent_sku or slug or "woocommerce-product",
    )
    return product

