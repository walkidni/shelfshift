import re
from collections.abc import Iterable

from slugify import slugify

from ...canonical import Product, Variant
from ...csv_schemas.woocommerce import (
    WOOCOMMERCE_WEIGHT_HEADER_BY_UNIT,
    woocommerce_columns_for_weight_unit,
)
from ..shared import utils
from ..shared.weight_units import resolve_weight_unit


class _WooCommerceExportHeaders:
    type = "Type"
    sku = "SKU"
    name = "Name"
    published = "Published"
    is_featured = "Is featured?"
    visibility_in_catalog = "Visibility in catalog"
    short_description = "Short description"
    description = "Description"
    tax_status = "Tax status"
    in_stock = "In stock?"
    stock = "Stock"
    backorders_allowed = "Backorders allowed?"
    sold_individually = "Sold individually?"
    regular_price = "Regular price"
    categories = "Categories"
    tags = "Tags"
    images = "Images"
    parent = "Parent"


H = _WooCommerceExportHeaders()
_WOOCOMMERCE_CANONICAL_HEADER_ATTRS = (
    "sku",
    "name",
    "published",
    "visibility_in_catalog",
    "short_description",
    "description",
    "tax_status",
    "in_stock",
    "stock",
    "regular_price",
    "categories",
    "tags",
    "images",
    "parent",
)
_WOOCOMMERCE_CANONICAL_HEADERS_BASE: set[str] = utils.infer_export_canonical_headers(
    export_headers=H,
    include_attrs=_WOOCOMMERCE_CANONICAL_HEADER_ATTRS,
    indexed_header_families=[(("Attribute {i} name", "Attribute {i} value(s)"), range(1, 3))],
)

_PLATFORM_TOKEN = {
    "shopify": "SH",
    "amazon": "AMZ",
    "aliexpress": "AE",
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _empty_row(columns: list[str]) -> dict[str, str]:
    return dict.fromkeys(columns, "")


def _set_cell(row: dict[str, str], header: str, value: str) -> None:
    if header not in row:
        raise ValueError(f"Unknown WooCommerce header assignment: {header}")
    row[header] = value


def _slug(value: str | None) -> str:
    if value is None:
        return ""
    return slugify(str(value).strip(), separator="-")


def _platform_token(platform: str | None) -> str:
    return _PLATFORM_TOKEN.get((platform or "").strip().lower(), "SRC")


def _resolve_product_key(product: Product) -> str:
    for candidate in (product.source.id, product.source.slug, product.title):
        key = _slug(candidate)
        if key:
            return key
    return "item"


def _resolve_parent_sku(product: Product) -> str:
    return f"{_platform_token(product.source.platform)}:{_resolve_product_key(product)}"


def _resolve_variant_key(variant: Variant, index: int) -> str:
    for candidate in (variant.id, variant.sku, variant.title):
        key = _slug(candidate)
        if key:
            return key
    return str(index)


def _resolve_option_names(product: Product, variants: list[Variant]) -> list[str]:
    names = [option.name for option in utils.resolve_option_defs(product) if option.name]
    if not names and len(variants) > 1:
        return ["Option"]
    return names[:3]


def _fallback_option_value(variant: Variant, index: int) -> str:
    return str(variant.title or variant.sku or variant.id or f"Variant {index}")


def _resolve_parent_attribute_values(
    variants: list[Variant],
    option_names: list[str],
    option_values_by_name: dict[str, list[str]],
    variant_option_maps: list[dict[str, str]],
) -> dict[str, list[str]]:
    values_by_option: dict[str, list[str]] = {}
    for option_name in option_names:
        values: list[str] = []
        if option_name != "Option":
            values.extend(option_values_by_name.get(option_name, []))
        for index, variant in enumerate(variants, start=1):
            if option_name == "Option":
                values.append(_fallback_option_value(variant, index))
            else:
                values.append(str(variant_option_maps[index - 1].get(option_name) or ""))
        values_by_option[option_name] = utils.ordered_unique(values)
    return values_by_option


def _resolve_price(product: Product, variant: Variant | None = None) -> str:
    amount = utils.resolve_price_amount(product, variant)
    return utils.format_number(amount, decimals=6) if amount is not None else ""


def _resolve_weight(product: Product, variant: Variant | None = None, *, unit: str) -> str:
    grams = utils.resolve_weight_grams(product, variant)
    converted = utils.convert_weight_from_grams(grams, unit=unit)
    if converted is None:
        return ""
    return utils.format_number(converted, decimals=6)


def _resolve_tags(product: Product) -> str:
    tags = sorted(utils.ordered_unique(product.tags or []), key=str.lower)
    return ",".join(tags)


def _resolve_images(images: Iterable[str]) -> str:
    return ",".join(utils.ordered_unique(str(image) for image in images))


def _strip_html(text: str | None) -> str:
    cleaned = _HTML_TAG_RE.sub(" ", text or "")
    return " ".join(cleaned.split())


def _resolve_short_description(product: Product) -> str:
    seo_description = utils.resolve_seo_description(product)
    if seo_description:
        return seo_description
    return _strip_html(product.description)


def _set_common_product_fields(
    row: dict[str, str],
    product: Product,
    *,
    is_visible: bool,
    include_descriptions: bool = True,
) -> None:
    _set_cell(row, H.published, "1" if is_visible else "0")
    _set_cell(row, H.is_featured, "0")
    _set_cell(row, H.visibility_in_catalog, "visible" if is_visible else "hidden")
    if include_descriptions:
        _set_cell(row, H.short_description, _resolve_short_description(product))
        _set_cell(row, H.description, product.description or "")
    _set_cell(row, H.tax_status, "none" if product.is_digital else "taxable")
    _set_cell(row, H.backorders_allowed, "0")
    _set_cell(row, H.sold_individually, "0")
    _set_cell(row, H.categories, utils.resolve_primary_category(product))
    _set_cell(row, H.tags, _resolve_tags(product))


def _variant_in_stock(variant: Variant) -> bool:
    quantity = utils.resolve_variant_inventory_quantity(variant)
    if quantity is not None:
        return quantity > 0
    available = utils.resolve_variant_available(variant)
    if available is not None:
        return bool(available)
    return True


def _apply_stock_fields(row: dict[str, str], variant: Variant) -> None:
    quantity = utils.resolve_variant_inventory_quantity(variant)
    if quantity is not None:
        qty = max(0, quantity)
        _set_cell(row, H.stock, str(qty))
        _set_cell(row, H.in_stock, "1" if qty > 0 else "0")
        return
    available = utils.resolve_variant_available(variant)
    if available is not None:
        _set_cell(row, H.in_stock, "1" if available else "0")
        return
    _set_cell(row, H.in_stock, "1")


def _set_attributes(
    row: dict[str, str],
    option_names: list[str],
    values_by_option: dict[str, str],
) -> None:
    for index, option_name in enumerate(option_names, start=1):
        value = values_by_option.get(option_name, "")
        _set_cell(row, f"Attribute {index} name", option_name)
        _set_cell(row, f"Attribute {index} value(s)", value)
        _set_cell(row, f"Attribute {index} visible", "1")
        _set_cell(row, f"Attribute {index} global", "0")


def _is_variable_product(product: Product, variants: list[Variant]) -> bool:
    if len(variants) > 1:
        return True
    for option in utils.resolve_option_defs(product):
        if len(utils.ordered_unique(option.values)) > 1:
            return True
    return False


def product_to_woocommerce_rows(
    product: Product,
    *,
    publish: bool | None = None,
    weight_unit: str = "kg",
) -> list[dict[str, str]]:
    resolved_weight_unit = resolve_weight_unit("woocommerce", weight_unit)
    resolved_columns = woocommerce_columns_for_weight_unit(resolved_weight_unit)
    resolved_weight_header = WOOCOMMERCE_WEIGHT_HEADER_BY_UNIT[resolved_weight_unit]
    canonical_headers = set(_WOOCOMMERCE_CANONICAL_HEADERS_BASE)
    canonical_headers.add(resolved_weight_header)
    is_visible = utils.resolve_product_visibility(product, publish_override=publish)
    variants = utils.resolve_variants(product)
    option_names = _resolve_option_names(product, variants)
    parent_sku = _resolve_parent_sku(product)
    images = utils.resolve_product_image_urls(product)
    option_values_by_name = {
        option.name: option.values
        for option in utils.resolve_option_defs(product)
        if option.name and option.name in option_names
    }
    variant_option_maps = [
        utils.resolve_variant_option_map(product, variant) for variant in variants
    ]
    parent_attribute_values = _resolve_parent_attribute_values(
        variants,
        option_names,
        option_values_by_name,
        variant_option_maps,
    )
    is_variable = _is_variable_product(product, variants)

    if not is_variable:
        variant = variants[0]
        row = _empty_row(resolved_columns)
        _set_common_product_fields(row, product, is_visible=is_visible)
        _set_cell(row, H.type, "simple")
        _set_cell(row, H.sku, parent_sku)
        _set_cell(row, H.name, product.title or "")
        _set_cell(row, H.regular_price, _resolve_price(product, variant))
        _set_cell(
            row,
            resolved_weight_header,
            _resolve_weight(
                product,
                variant,
                unit=resolved_weight_unit,
            ),
        )
        _set_cell(
            row,
            H.images,
            _resolve_images(images or [utils.resolve_variant_image_url(variant) or ""]),
        )
        _apply_stock_fields(row, variant)
        variant_option_values = variant_option_maps[0] if variant_option_maps else {}
        simple_values: dict[str, str] = {}
        for index, option_name in enumerate(option_names, start=1):
            if option_name == "Option":
                simple_values[option_name] = _fallback_option_value(variant, index)
            else:
                simple_values[option_name] = str(variant_option_values.get(option_name) or "")
        _set_attributes(row, option_names, simple_values)
        utils.apply_platform_unmapped_fields_to_row(
            row,
            product,
            platform="woocommerce",
            canonical_headers=canonical_headers,
        )
        utils.apply_platform_unmapped_fields_to_row(
            row,
            product,
            platform="woocommerce",
            canonical_headers=canonical_headers,
            variant=variant,
        )
        return [row]

    rows: list[dict[str, str]] = []
    parent_row = _empty_row(resolved_columns)
    _set_common_product_fields(parent_row, product, is_visible=is_visible)
    _set_cell(parent_row, H.type, "variable")
    _set_cell(parent_row, H.sku, parent_sku)
    _set_cell(parent_row, H.name, product.title or "")
    _set_cell(parent_row, H.regular_price, _resolve_price(product))
    _set_cell(
        parent_row, resolved_weight_header, _resolve_weight(product, unit=resolved_weight_unit)
    )
    _set_cell(parent_row, H.images, _resolve_images(images))
    _set_cell(parent_row, H.in_stock, "1" if any(_variant_in_stock(v) for v in variants) else "0")
    _set_attributes(
        parent_row,
        option_names,
        {name: ",".join(parent_attribute_values.get(name, [])) for name in option_names},
    )
    utils.apply_platform_unmapped_fields_to_row(
        parent_row,
        product,
        platform="woocommerce",
        canonical_headers=canonical_headers,
    )
    rows.append(parent_row)

    seen_skus = {parent_sku}
    for index, variant in enumerate(variants, start=1):
        variant_row = _empty_row(resolved_columns)
        _set_common_product_fields(
            variant_row,
            product,
            is_visible=is_visible,
            include_descriptions=False,
        )
        _set_cell(variant_row, H.type, "variation")
        variant_sku_base = f"{parent_sku}:{_resolve_variant_key(variant, index)}"
        variant_sku = variant_sku_base
        suffix = 2
        while variant_sku in seen_skus:
            variant_sku = f"{variant_sku_base}-{suffix}"
            suffix += 1
        seen_skus.add(variant_sku)

        _set_cell(variant_row, H.sku, variant_sku)
        _set_cell(variant_row, H.regular_price, _resolve_price(product, variant))
        _set_cell(
            variant_row,
            resolved_weight_header,
            _resolve_weight(
                product,
                variant,
                unit=resolved_weight_unit,
            ),
        )
        _set_cell(variant_row, H.images, utils.resolve_variant_image_url(variant))
        _set_cell(variant_row, H.parent, parent_sku)
        _set_cell(variant_row, H.categories, "")
        _set_cell(variant_row, H.tags, "")

        _apply_stock_fields(variant_row, variant)

        variant_option_values = variant_option_maps[index - 1]
        variant_values: dict[str, str] = {}
        for option_name in option_names:
            if option_name == "Option":
                variant_values[option_name] = _fallback_option_value(variant, index)
            else:
                variant_values[option_name] = str(variant_option_values.get(option_name) or "")
        _set_attributes(variant_row, option_names, variant_values)
        utils.apply_platform_unmapped_fields_to_row(
            variant_row,
            product,
            platform="woocommerce",
            canonical_headers=canonical_headers,
            variant=variant,
        )
        rows.append(variant_row)

    return rows


def product_to_woocommerce_csv(
    product: Product,
    *,
    publish: bool | None = None,
    weight_unit: str = "kg",
) -> tuple[str, str]:
    columns = woocommerce_columns_for_weight_unit(weight_unit)
    rows = product_to_woocommerce_rows(product, publish=publish, weight_unit=weight_unit)
    return utils.dict_rows_to_csv(rows, columns), utils.make_export_filename("woocommerce")
