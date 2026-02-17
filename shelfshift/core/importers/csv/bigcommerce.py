import re

from ...canonical import Identifiers, Inventory, Product, Seo, SourceRef, Variant
from ...exporters.platforms.bigcommerce import BIGCOMMERCE_COLUMNS, BIGCOMMERCE_LEGACY_COLUMNS

from .common import (
    add_csv_provenance,
    apply_extra_product_fields,
    apply_extra_variant_fields,
    csv_rows,
    media_from_urls,
    option_defs_from_option_maps,
    parse_float,
    parse_int,
    price_from_amount,
    require_headers,
    split_tokens,
    taxonomy_from_primary,
    weight_object,
    weight_to_grams,
)


_MODERN_REQUIRED_HEADERS = ("Item", "Name", "Type", "SKU", "Price")
_LEGACY_REQUIRED_HEADERS = ("Product Type", "Code", "Name", "Calculated Price")
_OPTION_RE = re.compile(r"\|Name=([^|]+)\|Value=([^|]+)$")


def _parse_modern_options(value: str) -> dict[str, str]:
    out: dict[str, str] = {}
    text = str(value or "").strip()
    if not text:
        return out
    for token in text.split("Type="):
        candidate = token.strip()
        if not candidate:
            continue
        match = _OPTION_RE.search(candidate)
        if not match:
            continue
        out[match.group(1).strip()] = match.group(2).strip()
    return out


def _parse_legacy_images(value: str) -> list[str]:
    urls: list[str] = []
    for token in str(value or "").split("|"):
        stripped = token.strip()
        if not stripped:
            continue
        if ":" in stripped:
            stripped = stripped.split(":", 1)[1].strip()
        if stripped:
            urls.append(stripped)
    return urls


def _parse_modern(csv_text: str, *, source_weight_unit: str) -> Product:
    headers, rows = csv_rows(csv_text)
    require_headers(headers, _MODERN_REQUIRED_HEADERS)
    known_headers = set(BIGCOMMERCE_COLUMNS)

    product_indices = [
        index
        for index, row in enumerate(rows)
        if str(row.get("Item") or "").strip().lower() == "product"
    ]
    if not product_indices:
        raise ValueError("BigCommerce modern CSV requires at least one Product row.")
    start = product_indices[0]
    end = product_indices[1] if len(product_indices) > 1 else len(rows)
    selected_rows = rows[start:end]
    product_row = selected_rows[0]

    variant_rows = [
        row for row in selected_rows if str(row.get("Item") or "").strip().lower() == "variant"
    ]
    image_rows = [row for row in selected_rows if str(row.get("Item") or "").strip().lower() == "image"]

    option_maps: list[dict[str, str]] = []
    variants: list[Variant] = []
    for index, row in enumerate(variant_rows, start=1):
        sku = str(row.get("SKU") or "").strip() or f"BC:{index}"
        option_map = _parse_modern_options(str(row.get("Options") or ""))
        option_maps.append(option_map)
        quantity = parse_int(row.get("Current Stock"))
        variant = Variant(
            id=str(index),
            sku=sku,
            title=" / ".join(option_map.values()) or None,
            option_values=[{"name": key, "value": value} for key, value in option_map.items()],
            price=price_from_amount(parse_float(row.get("Price"))),
            inventory=Inventory(
                track_quantity=(quantity is not None),
                quantity=quantity,
                available=(quantity > 0 if quantity is not None else True),
            ),
            media=media_from_urls([str(row.get("Variant Image URL") or "").strip()], variant_sku=sku),
            identifiers=Identifiers(values={"source_variant_id": str(index), "sku": sku}),
        )
        apply_extra_variant_fields(variant, row, known_headers=known_headers)
        variants.append(variant)

    if not variants:
        fallback_sku = str(product_row.get("SKU") or "").strip() or "BC:product"
        variants = [
            Variant(
                id="1",
                sku=fallback_sku,
                price=price_from_amount(parse_float(product_row.get("Price"))),
                inventory=Inventory(track_quantity=False, quantity=None, available=True),
                identifiers=Identifiers(values={"source_variant_id": "1", "sku": fallback_sku}),
            )
        ]

    image_urls = [str(row.get("Image URL (Import)") or "").strip() for row in image_rows]
    weight = weight_object(weight_to_grams(product_row.get("Weight"), source_weight_unit=source_weight_unit))
    type_value = str(product_row.get("Type") or "").strip().lower()
    is_digital = type_value == "digital"
    product = Product(
        source=SourceRef(
            platform="bigcommerce",
            id=str(product_row.get("ID") or "").strip() or str(product_row.get("SKU") or "").strip() or None,
            slug=str(product_row.get("Product URL") or "").strip().strip("/") or None,
            url=None,
        ),
        title=str(product_row.get("Name") or "").strip() or None,
        description=str(product_row.get("Description") or "").strip() or None,
        seo=Seo(
            title=str(product_row.get("Page Title") or "").strip() or None,
            description=str(product_row.get("Meta Description") or "").strip() or None,
        ),
        tags=split_tokens(product_row.get("Search Keywords"), sep=","),
        taxonomy=taxonomy_from_primary(str(product_row.get("Categories") or "").strip() or None),
        variants=variants,
        options=option_defs_from_option_maps(option_maps),
        price=price_from_amount(parse_float(product_row.get("Price"))),
        weight=weight,
        requires_shipping=not is_digital,
        track_quantity=any(variant.inventory.track_quantity for variant in variants),
        is_digital=is_digital,
        media=media_from_urls(image_urls),
        identifiers=Identifiers(values={"source_product_id": str(product_row.get("ID") or "").strip() or variants[0].sku}),
    )
    apply_extra_product_fields(product, product_row, known_headers=known_headers)
    add_csv_provenance(
        product,
        source_platform="bigcommerce",
        detected_product_count=len(product_indices),
        selected_product_key=str(product_row.get("SKU") or "").strip() or str(product_row.get("Name") or "").strip(),
    )
    return product


def _parse_legacy(csv_text: str, *, source_weight_unit: str) -> Product:
    headers, rows = csv_rows(csv_text)
    require_headers(headers, _LEGACY_REQUIRED_HEADERS)
    known_headers = set(BIGCOMMERCE_LEGACY_COLUMNS)
    product_row = rows[0]

    sku = str(product_row.get("Code") or "").strip() or "BC:legacy"
    quantity = parse_int(product_row.get("Stock Level"))
    weight = weight_object(weight_to_grams(product_row.get("Weight"), source_weight_unit=source_weight_unit))
    variant = Variant(
        id="1",
        sku=sku,
        price=price_from_amount(
            parse_float(product_row.get("Calculated Price"))
            or parse_float(product_row.get("Sale Price"))
            or parse_float(product_row.get("Retail Price"))
        ),
        inventory=Inventory(
            track_quantity=(quantity is not None),
            quantity=quantity,
            available=(quantity > 0 if quantity is not None else True),
        ),
        weight=weight,
        identifiers=Identifiers(values={"source_variant_id": "1", "sku": sku}),
    )
    apply_extra_variant_fields(variant, product_row, known_headers=known_headers)

    product = Product(
        source=SourceRef(
            platform="bigcommerce",
            id=str(product_row.get("Product ID") or "").strip() or sku,
            slug=str(product_row.get("Product URL") or "").strip().strip("/") or None,
            url=None,
        ),
        title=str(product_row.get("Name") or "").strip() or None,
        description=str(product_row.get("Description") or "").strip() or None,
        seo=Seo(
            title=str(product_row.get("Page Title") or "").strip() or None,
            description=str(product_row.get("META Description") or "").strip() or None,
        ),
        brand=str(product_row.get("Brand") or "").strip() or None,
        vendor=str(product_row.get("Brand") or "").strip() or None,
        tags=split_tokens(product_row.get("META Keywords"), sep=","),
        taxonomy=taxonomy_from_primary(str(product_row.get("Category Details") or "").strip() or None),
        variants=[variant],
        price=variant.price,
        weight=weight,
        requires_shipping=True,
        track_quantity=(quantity is not None),
        is_digital=False,
        media=media_from_urls(_parse_legacy_images(str(product_row.get("Images") or ""))),
        identifiers=Identifiers(values={"source_product_id": str(product_row.get("Product ID") or "").strip() or sku}),
    )
    apply_extra_product_fields(product, product_row, known_headers=known_headers)
    add_csv_provenance(
        product,
        source_platform="bigcommerce",
        detected_product_count=len(rows),
        selected_product_key=sku,
    )
    return product


def parse_bigcommerce_csv(csv_text: str, *, source_weight_unit: str) -> Product:
    headers, _rows = csv_rows(csv_text)
    header_set = set(headers)
    if {"Item", "SKU", "Name"}.issubset(header_set):
        return _parse_modern(csv_text, source_weight_unit=source_weight_unit)
    if {"Product Type", "Code", "Name"}.issubset(header_set):
        return _parse_legacy(csv_text, source_weight_unit=source_weight_unit)
    raise ValueError("Unable to detect BigCommerce CSV format from headers.")

