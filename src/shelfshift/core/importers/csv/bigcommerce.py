import re
from typing import Literal

from ...canonical import Inventory, Product, Seo, SourceRef, Variant
from ...csv_schemas.bigcommerce import (
    BIGCOMMERCE_LEGACY_DETECTION_HEADERS,
    BIGCOMMERCE_LEGACY_HEADER_ALIASES,
    BIGCOMMERCE_LEGACY_REQUIRED_HEADERS,
    BIGCOMMERCE_MODERN_DETECTION_HEADERS,
    BIGCOMMERCE_MODERN_HEADER_ALIASES,
    BIGCOMMERCE_MODERN_REQUIRED_HEADERS,
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
    require_headers,
    split_tokens,
    taxonomy_from_primary,
    unmapped_headers_from_csv,
    weight_object,
    weight_to_grams,
)

_OPTION_RE = re.compile(r"\|Name=([^|]+)\|Value=([^|]+)$")
_MODERN_CANONICAL_MAPPED_HEADERS: set[str] = infer_mapped_headers(
    alias_maps=[BIGCOMMERCE_MODERN_HEADER_ALIASES]
)
_LEGACY_CANONICAL_MAPPED_HEADERS: set[str] = infer_mapped_headers(
    alias_maps=[BIGCOMMERCE_LEGACY_HEADER_ALIASES]
)

BigCommerceCsvInputFormat = Literal["modern", "legacy"]


def _first_non_empty(row: dict[str, str], *headers: str) -> str:
    for header in headers:
        value = str(row.get(header) or "").strip()
        if value:
            return value
    return ""


def _field_value(
    row: dict[str, str],
    *,
    aliases: dict[str, tuple[str, ...]],
    field: str,
) -> str:
    return _first_non_empty(row, *aliases[field])


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
    require_headers(headers, BIGCOMMERCE_MODERN_REQUIRED_HEADERS)
    unmapped_headers = unmapped_headers_from_csv(
        headers,
        mapped_headers=_MODERN_CANONICAL_MAPPED_HEADERS,
    )
    product_indices = [
        index
        for index, row in enumerate(rows)
        if str(row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["item"][0]) or "").strip().lower()
        == "product"
    ]
    if not product_indices:
        raise ValueError("BigCommerce modern CSV requires at least one Product row.")
    start = product_indices[0]
    end = product_indices[1] if len(product_indices) > 1 else len(rows)
    selected_rows = rows[start:end]
    product_row = selected_rows[0]

    variant_rows = [
        row
        for row in selected_rows
        if str(row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["item"][0]) or "").strip().lower()
        == "variant"
    ]
    image_rows = [
        row
        for row in selected_rows
        if str(row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["item"][0]) or "").strip().lower()
        == "image"
    ]

    option_maps: list[dict[str, str]] = []
    variants: list[Variant] = []
    variant_source_rows: list[dict[str, str]] = list(variant_rows)
    for index, row in enumerate(variant_rows, start=1):
        sku = (
            str(row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["sku"][0]) or "").strip() or f"BC:{index}"
        )
        option_map = _parse_modern_options(
            str(row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["options"][0]) or "")
        )
        option_maps.append(option_map)
        quantity = parse_int(row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["current_stock"][0]))
        variant = Variant(
            id=str(index),
            sku=sku,
            title=" / ".join(option_map.values()) or None,
            option_values=[{"name": key, "value": value} for key, value in option_map.items()],
            price=price_from_amount(
                parse_float(row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["price"][0]))
            ),
            inventory=Inventory(
                track_quantity=(quantity is not None),
                quantity=quantity,
                available=(quantity > 0 if quantity is not None else True),
            ),
            media=media_from_urls(
                [
                    str(
                        row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["variant_image_url"][0]) or ""
                    ).strip()
                ],
                variant_sku=sku,
            ),
            identifiers=make_identifiers({"source_variant_id": str(index), "sku": sku}),
        )
        variants.append(variant)

    if not variants:
        fallback_sku = (
            str(product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["sku"][0]) or "").strip()
            or "BC:product"
        )
        variant_source_rows = [product_row]
        variants = [
            Variant(
                id="1",
                sku=fallback_sku,
                price=price_from_amount(
                    parse_float(product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["price"][0]))
                ),
                inventory=Inventory(track_quantity=False, quantity=None, available=True),
                identifiers=make_identifiers({"source_variant_id": "1", "sku": fallback_sku}),
            )
        ]

    image_urls = [
        str(row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["image_url_import"][0]) or "").strip()
        for row in image_rows
    ]
    weight = weight_object(
        weight_to_grams(
            product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["weight"][0]),
            source_weight_unit=source_weight_unit,
        )
    )
    type_value = (
        str(product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["type"][0]) or "").strip().lower()
    )
    is_digital = type_value == "digital"
    is_published = parse_bool(product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["is_visible"][0]))
    product = Product(
        source=SourceRef(
            platform="bigcommerce",
            id=str(product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["id"][0]) or "").strip()
            or None,
            slug=str(product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["product_url"][0]) or "")
            .strip()
            .strip("/")
            or None,
            url=None,
        ),
        title=str(product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["name"][0]) or "").strip()
        or None,
        description=str(
            product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["description"][0]) or ""
        ).strip()
        or None,
        seo=Seo(
            title=str(
                product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["page_title"][0]) or ""
            ).strip()
            or None,
            description=str(
                product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["meta_description"][0]) or ""
            ).strip()
            or None,
        ),
        tags=split_tokens(
            product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["search_keywords"][0]),
            sep=",",
        ),
        taxonomy=taxonomy_from_primary(
            str(product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["categories"][0]) or "").strip()
            or None
        ),
        variants=variants,
        options=option_defs_from_option_maps(option_maps),
        price=price_from_amount(
            parse_float(product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["price"][0]))
        ),
        weight=weight,
        requires_shipping=not is_digital,
        track_quantity=any(variant.inventory.track_quantity for variant in variants),
        is_digital=is_digital,
        is_published=is_published,
        media=media_from_urls(image_urls),
        identifiers=make_identifiers(
            values={
                "source_product_id": str(
                    product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["id"][0]) or ""
                ).strip()
                or variants[0].sku
            }
        ),
    )
    apply_first_non_empty_unmapped_fields(
        product.unmapped_fields,
        platform="bigcommerce",
        rows=[product_row],
        headers=unmapped_headers,
    )
    for variant, row in zip(variants, variant_source_rows, strict=False):
        apply_row_unmapped_fields(
            variant.unmapped_fields,
            platform="bigcommerce",
            row=row,
            headers=unmapped_headers,
        )
    add_csv_provenance(
        product,
        source_platform="bigcommerce",
        detected_product_count=len(product_indices),
        selected_product_key=str(
            product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["sku"][0]) or ""
        ).strip()
        or str(product_row.get(BIGCOMMERCE_MODERN_HEADER_ALIASES["name"][0]) or "").strip(),
    )
    return product


def _parse_legacy(csv_text: str, *, source_weight_unit: str) -> Product:
    headers, rows = csv_rows(csv_text)
    require_headers(headers, BIGCOMMERCE_LEGACY_REQUIRED_HEADERS)
    unmapped_headers = unmapped_headers_from_csv(
        headers,
        mapped_headers=_LEGACY_CANONICAL_MAPPED_HEADERS,
    )
    product_row = rows[0]

    sku = (
        _field_value(product_row, aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES, field="code")
        or "BC:legacy"
    )
    quantity = parse_int(
        _field_value(
            product_row,
            aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
            field="stock_level",
        )
    )
    weight = weight_object(
        weight_to_grams(
            _field_value(
                product_row,
                aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                field="weight",
            ),
            source_weight_unit=source_weight_unit,
        )
    )
    variant = Variant(
        id="1",
        sku=sku,
        price=price_from_amount(
            parse_float(
                _field_value(
                    product_row,
                    aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                    field="calculated_price",
                )
            )
            or parse_float(
                _field_value(
                    product_row,
                    aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                    field="sale_price",
                )
            )
            or parse_float(
                _field_value(
                    product_row,
                    aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                    field="retail_price",
                )
            )
        ),
        inventory=Inventory(
            track_quantity=(quantity is not None),
            quantity=quantity,
            available=(quantity > 0 if quantity is not None else True),
        ),
        weight=weight,
        identifiers=make_identifiers({"source_variant_id": "1", "sku": sku}),
    )
    product = Product(
        source=SourceRef(
            platform="bigcommerce",
            id=_field_value(
                product_row,
                aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                field="product_id",
            )
            or None,
            slug=_field_value(
                product_row,
                aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                field="product_url",
            ).strip("/")
            or None,
            url=None,
        ),
        title=_field_value(
            product_row,
            aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
            field="name",
        )
        or None,
        description=_field_value(
            product_row,
            aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
            field="description",
        )
        or None,
        seo=Seo(
            title=_field_value(
                product_row,
                aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                field="page_title",
            )
            or None,
            description=_field_value(
                product_row,
                aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                field="meta_description",
            )
            or None,
        ),
        brand=_field_value(
            product_row,
            aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
            field="brand",
        )
        or None,
        vendor=_field_value(
            product_row,
            aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
            field="brand",
        )
        or None,
        tags=split_tokens(
            _field_value(
                product_row,
                aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                field="meta_keywords",
            ),
            sep=",",
        ),
        taxonomy=taxonomy_from_primary(
            _field_value(
                product_row,
                aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                field="category_details",
            )
            or None
        ),
        variants=[variant],
        price=variant.price,
        weight=weight,
        requires_shipping=True,
        track_quantity=(quantity is not None),
        is_digital=False,
        is_published=parse_bool(
            _field_value(
                product_row,
                aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                field="product_visible",
            )
        ),
        media=media_from_urls(
            _parse_legacy_images(
                _field_value(
                    product_row,
                    aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                    field="images",
                )
            )
        ),
        identifiers=make_identifiers(
            values={
                "source_product_id": _field_value(
                    product_row,
                    aliases=BIGCOMMERCE_LEGACY_HEADER_ALIASES,
                    field="product_id",
                )
                or sku
            }
        ),
    )
    apply_first_non_empty_unmapped_fields(
        product.unmapped_fields,
        platform="bigcommerce",
        rows=[product_row],
        headers=unmapped_headers,
    )
    apply_row_unmapped_fields(
        variant.unmapped_fields,
        platform="bigcommerce",
        row=product_row,
        headers=unmapped_headers,
    )
    add_csv_provenance(
        product,
        source_platform="bigcommerce",
        detected_product_count=len(rows),
        selected_product_key=sku,
    )
    return product


def detect_bigcommerce_csv_format(headers: list[str]) -> BigCommerceCsvInputFormat:
    header_set = set(headers)
    if BIGCOMMERCE_MODERN_DETECTION_HEADERS.issubset(header_set):
        return "modern"
    if BIGCOMMERCE_LEGACY_DETECTION_HEADERS.issubset(header_set):
        return "legacy"
    raise ValueError("Unable to detect BigCommerce CSV format from headers.")


def parse_bigcommerce_csv(csv_text: str, *, source_weight_unit: str) -> Product:
    headers, _rows = csv_rows(csv_text)
    csv_format = detect_bigcommerce_csv_format(headers)
    if csv_format == "modern":
        return _parse_modern(csv_text, source_weight_unit=source_weight_unit)
    return _parse_legacy(csv_text, source_weight_unit=source_weight_unit)


__all__ = ["detect_bigcommerce_csv_format", "parse_bigcommerce_csv"]
