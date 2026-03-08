import re
from typing import Literal

from slugify import slugify

from ...canonical import Product, Variant
from ..shared import utils
from ..shared.weight_units import resolve_weight_unit

# BigCommerce Modern Product Import/Export (v3) schema.
BIGCOMMERCE_COLUMNS: list[str] = [
    "Item",
    "ID",
    "Name",
    "Type",
    "SKU",
    "Options",
    "Inventory Tracking",
    "Current Stock",
    "Low Stock",
    "Price",
    "Cost Price",
    "Retail Price",
    "Sale Price",
    "Brand ID",
    "Channels",
    "Categories",
    "Description",
    "Custom Fields",
    "Page Title",
    "Product URL",
    "Meta Description",
    "Search Keywords",
    "Meta Keywords",
    "Bin Picking Number",
    "UPC/EAN",
    "Global Trade Number",
    "Manufacturer Part Number",
    "Free Shipping",
    "Fixed Shipping Cost",
    "Weight",
    "Width",
    "Height",
    "Depth",
    "Is Visible",
    "Is Featured",
    "Warranty",
    "Tax Class",
    "Product Condition",
    "Show Product Condition",
    "Sort Order",
    "Variant Image URL",
    "Internal Image URL (Export)",
    "Image URL (Import)",
    "Image Description",
    "Image is Thumbnail",
    "Image Sort Order",
    "YouTube ID",
    "Video Title",
    "Video Description",
    "Video Sort Order",
]

BIGCOMMERCE_LEGACY_COLUMNS: list[str] = [
    "Item Type",
    "Product ID",
    "Product Name",
    "Product Type",
    "Product Code/SKU",
    "Bin Picking Number",
    "Brand Name",
    "Option Set",
    "Option Set Align",
    "Product Description",
    "Price",
    "Cost Price",
    "Retail Price",
    "Sale Price",
    "Fixed Shipping Cost",
    "Free Shipping",
    "Product Warranty",
    "Product Weight",
    "Product Width",
    "Product Height",
    "Product Depth",
    "Allow Purchases?",
    "Product Visible?",
    "Product Availability",
    "Track Inventory",
    "Current Stock Level",
    "Low Stock Level",
    "Category",
    "Product Image ID - 1",
    "Product Image File - 1",
    "Product Image Description - 1",
    "Product Image Is Thumbnail - 1",
    "Product Image Sort - 1",
    "Product Image ID - 2",
    "Product Image File - 2",
    "Product Image Description - 2",
    "Product Image Is Thumbnail - 2",
    "Product Image Sort - 2",
    "Search Keywords",
    "Page Title",
    "Meta Keywords",
    "Meta Description",
    "MYOB Asset Acct",
    "MYOB Income Acct",
    "MYOB Expense Acct",
    "Product Condition",
    "Show Product Condition?",
    "Event Date Required?",
    "Event Date Name",
    "Event Date Is Limited?",
    "Event Date Start Date",
    "Event Date End Date",
    "Sort Order",
    "Product Tax Class",
    "Product UPC/EAN",
    "Stop Processing Rules",
    "Product URL",
    "Redirect Old URL?",
    "Global Trade Item Number",
    "Manufacturer Part Number",
]


class _BigCommerceModernHeaders:
    item = "Item"
    type = "Type"
    name = "Name"
    description = "Description"
    sku = "SKU"
    price = "Price"
    categories = "Categories"
    weight = "Weight"
    inventory_tracking = "Inventory Tracking"
    current_stock = "Current Stock"
    low_stock = "Low Stock"
    product_url = "Product URL"
    meta_description = "Meta Description"
    search_keywords = "Search Keywords"
    meta_keywords = "Meta Keywords"
    free_shipping = "Free Shipping"
    is_visible = "Is Visible"
    is_featured = "Is Featured"
    tax_class = "Tax Class"
    product_condition = "Product Condition"
    show_product_condition = "Show Product Condition"
    sort_order = "Sort Order"
    options = "Options"
    variant_image_url = "Variant Image URL"
    image_url_import = "Image URL (Import)"
    image_is_thumbnail = "Image is Thumbnail"
    image_sort_order = "Image Sort Order"


class _BigCommerceLegacyHeaders:
    item_type = "Item Type"
    product_id = "Product ID"
    product_type = "Product Type"
    product_code_sku = "Product Code/SKU"
    product_name = "Product Name"
    brand_name = "Brand Name"
    product_description = "Product Description"
    price = "Price"
    fixed_shipping_cost = "Fixed Shipping Cost"
    free_shipping = "Free Shipping"
    product_weight = "Product Weight"
    allow_purchases = "Allow Purchases?"
    product_visible = "Product Visible?"
    track_inventory = "Track Inventory"
    current_stock_level = "Current Stock Level"
    low_stock_level = "Low Stock Level"
    category = "Category"
    product_image_file_1 = "Product Image File - 1"
    product_image_file_2 = "Product Image File - 2"
    search_keywords = "Search Keywords"
    page_title = "Page Title"
    meta_keywords = "Meta Keywords"
    meta_description = "Meta Description"
    product_condition = "Product Condition"
    product_url = "Product URL"


MH = _BigCommerceModernHeaders()
LH = _BigCommerceLegacyHeaders()
_BIGCOMMERCE_MODERN_CANONICAL_HEADERS: set[str] = utils.infer_export_canonical_headers(
    export_headers=MH
)
_BIGCOMMERCE_LEGACY_CANONICAL_HEADERS: set[str] = utils.infer_export_canonical_headers(
    export_headers=LH
)


BigCommerceCsvFormat = Literal["modern", "legacy"]

_PLATFORM_TOKEN = {
    "shopify": "SH",
    "amazon": "AMZ",
    "aliexpress": "AE",
    "squarespace": "SQ",
    "woocommerce": "WC",
}

_INVENTORY_NONE = "none"
_INVENTORY_PRODUCT = "product"
_INVENTORY_VARIANT = "variant"
_DEFAULT_OPTION_TYPE = "Rectangle"
_COLOR_OPTION_TYPE = "Swatch"
_SWATCH_VALUE_DATA_RE = re.compile(r"\[#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\]$")


def _empty_row() -> dict[str, str]:
    return dict.fromkeys(BIGCOMMERCE_COLUMNS, "")


def _empty_legacy_row() -> dict[str, str]:
    return dict.fromkeys(BIGCOMMERCE_LEGACY_COLUMNS, "")


def _set_cell(row: dict[str, str], header: str, value: str, *, schema: str) -> None:
    if header not in row:
        raise ValueError(f"Unknown BigCommerce {schema} header assignment: {header}")
    row[header] = value


def _format_price(value: float | None) -> str:
    return utils.format_number(value, decimals=6) if value is not None else ""


def _format_weight(value: float | None, *, weight_unit: str, decimals: int) -> str:
    if value is None:
        return ""
    converted = utils.convert_weight_from_grams(value, unit=weight_unit)
    if converted is None:
        return ""
    return utils.format_number(converted, decimals=decimals)


def _require_weight(value: float | None, *, is_digital: bool, weight_unit: str) -> str:
    if is_digital:
        return ""
    formatted = _format_weight(value, weight_unit=weight_unit, decimals=6)
    return formatted or "0"


def _resolve_price(product: Product, variant: Variant | None = None) -> str:
    amount = utils.resolve_price_amount(product, variant)
    return _format_price(amount)


def _resolve_product_key(product: Product) -> str:
    for candidate in (product.source.id, product.source.slug, product.title):
        key = slugify(str(candidate or ""), separator="-")
        if key:
            return key
    return "item"


def _platform_token(platform: str | None) -> str:
    return _PLATFORM_TOKEN.get((platform or "").strip().lower(), "SRC")


def _resolve_parent_sku(product: Product, variants: list[Variant], *, is_variable: bool) -> str:
    if not is_variable and variants:
        sku = (variants[0].sku or "").strip()
        if sku:
            return sku
    return f"{_platform_token(product.source.platform)}-{_resolve_product_key(product)}".upper()


def _resolve_variant_sku(parent_sku: str, variant: Variant, *, index: int) -> str:
    return str(variant.sku or variant.id or f"{parent_sku}-{index}")


def _resolve_inventory_qty(variant: Variant) -> str:
    qty = utils.resolve_variant_inventory_quantity(variant)
    if qty is None:
        return ""
    return str(qty)


def _has_any_inventory_quantity(variants: list[Variant]) -> bool:
    return any(_resolve_inventory_qty(variant) != "" for variant in variants)


def _resolve_option_names(product: Product, variants: list[Variant]) -> list[str]:
    option_names = [option.name for option in utils.resolve_option_defs(product) if option.name]
    if not option_names and len(variants) > 1:
        return ["Option"]
    return option_names


def _is_variable_product(
    product: Product, variants: list[Variant], option_names: list[str]
) -> bool:
    if len(variants) > 1:
        return True
    if option_names:
        return True
    for option in utils.resolve_option_defs(product):
        if len(utils.ordered_unique(option.values)) > 1:
            return True
    return False


def _fallback_variant_option_value(variant: Variant, index: int) -> str:
    return str(variant.title or variant.sku or variant.id or f"Variant {index}")


def _normalize_image_url(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        return f"https:{raw}"
    if raw.startswith(("http://", "https://")):
        return raw
    return ""


def _sanitize_option_token_value(value: str) -> str:
    return " ".join(value.replace("|", "/").replace("\n", " ").split())


def _is_color_option(option_name: str) -> bool:
    normalized = (option_name or "").strip().lower()
    return normalized in {"color", "colour"}


def _resolve_option_type(option_name: str, option_value: str) -> str:
    if _is_color_option(option_name) and _SWATCH_VALUE_DATA_RE.search(option_value):
        return _COLOR_OPTION_TYPE
    return _DEFAULT_OPTION_TYPE


def _build_variant_options_value(
    variant: Variant,
    option_names: list[str],
    *,
    index: int,
    values_by_name: dict[str, str],
) -> str:
    chunks: list[str] = []
    for option_name in option_names:
        if option_name == "Option":
            raw_value = _fallback_variant_option_value(variant, index)
        else:
            raw_value = str(values_by_name.get(option_name) or "")
            if not raw_value:
                raw_value = _fallback_variant_option_value(variant, index)
        safe_name = _sanitize_option_token_value(option_name)
        safe_value = _sanitize_option_token_value(raw_value)
        option_type = _resolve_option_type(option_name, safe_value)
        chunks.append(f"Type={option_type}|Name={safe_name}|Value={safe_value}")
    return "".join(chunks)


def _resolve_inventory_mode(*, is_variable: bool, has_inventory: bool) -> str:
    if not has_inventory:
        return _INVENTORY_NONE
    if is_variable:
        return _INVENTORY_VARIANT
    return _INVENTORY_PRODUCT


def _resolve_product_url_slug(product: Product) -> str:
    if product.source.slug:
        cleaned = slugify(product.source.slug, separator="-")
        if cleaned:
            return f"/{cleaned}/"
    title_slug = slugify(str(product.title or ""), separator="-")
    if title_slug:
        return f"/{title_slug}/"
    return ""


def _resolve_stock_for_product_row(variants: list[Variant], *, inventory_mode: str) -> str:
    if inventory_mode != _INVENTORY_PRODUCT:
        return "0"
    if not variants:
        return "0"
    value = _resolve_inventory_qty(variants[0])
    return value or "0"


def _resolve_stock_for_variant_row(variant: Variant) -> str:
    value = _resolve_inventory_qty(variant)
    return value or "0"


def _resolve_keywords_from_tags(tags: list[str] | None) -> str:
    return ",".join(utils.ordered_unique(tags or []))


def _resolve_product_weight_grams(product: Product, variants: list[Variant]) -> float | None:
    for variant in variants:
        grams = utils.resolve_weight_grams(product, variant)
        if grams is not None:
            return grams
    return utils.resolve_weight_grams(product)


def _resolve_category_details(category: str | None) -> str:
    value = str(category or "").strip()
    if not value:
        return ""
    return f"Category Name: {value}, Category Path: {value}"


def _resolve_modern_categories(product: Product) -> str:
    # BigCommerce's modern import flow expects category IDs (integers) in the
    # Categories column. Emitting category names from upstream sources causes
    # import failures (e.g. "Invalid Category ID format").
    return ""


def _resolve_legacy_image_urls(product: Product) -> list[str]:
    return utils.ordered_unique(
        [
            url
            for url in (
                _normalize_image_url(image) for image in utils.resolve_product_image_urls(product)
            )
            if url
        ]
    )


def _product_to_bigcommerce_legacy_rows(
    product: Product,
    *,
    publish: bool | None = None,
    weight_unit: str,
) -> list[dict[str, str]]:
    is_visible = utils.resolve_product_visibility(product, publish_override=publish)
    variants = utils.resolve_variants(product)
    option_names = _resolve_option_names(product, variants)
    is_variable = _is_variable_product(product, variants, option_names)
    has_inventory = _has_any_inventory_quantity(variants)
    inventory_mode = _resolve_inventory_mode(is_variable=is_variable, has_inventory=has_inventory)
    parent_sku = _resolve_parent_sku(product, variants, is_variable=is_variable)
    first_variant = variants[0] if variants else None

    row = _empty_legacy_row()
    _set_cell(row, LH.item_type, "Product", schema="legacy")
    _set_cell(row, LH.product_id, str(product.source.id or ""), schema="legacy")
    _set_cell(row, LH.product_type, "P", schema="legacy")
    _set_cell(row, LH.product_code_sku, parent_sku, schema="legacy")
    _set_cell(row, LH.product_name, product.title or "", schema="legacy")
    _set_cell(row, LH.brand_name, product.brand or "", schema="legacy")
    _set_cell(row, LH.product_description, product.description or "", schema="legacy")
    _set_cell(row, LH.price, _resolve_price(product, first_variant), schema="legacy")
    _set_cell(row, LH.fixed_shipping_cost, "0.0000", schema="legacy")
    _set_cell(row, LH.free_shipping, "Y" if not product.requires_shipping else "N", schema="legacy")
    _set_cell(
        row,
        LH.product_weight,
        _format_weight(
            _resolve_product_weight_grams(product, variants), weight_unit=weight_unit, decimals=4
        ),
        schema="legacy",
    )
    _set_cell(row, LH.allow_purchases, "Y", schema="legacy")
    _set_cell(row, LH.product_visible, "Y" if is_visible else "N", schema="legacy")
    _set_cell(
        row, LH.track_inventory, "Y" if inventory_mode != _INVENTORY_NONE else "N", schema="legacy"
    )
    _set_cell(
        row,
        LH.current_stock_level,
        _resolve_stock_for_product_row(variants, inventory_mode=inventory_mode),
        schema="legacy",
    )
    _set_cell(row, LH.low_stock_level, "0", schema="legacy")
    _set_cell(row, LH.category, utils.resolve_primary_category(product), schema="legacy")
    image_urls = _resolve_legacy_image_urls(product)
    if image_urls:
        _set_cell(row, LH.product_image_file_1, image_urls[0], schema="legacy")
    if len(image_urls) > 1:
        _set_cell(row, LH.product_image_file_2, image_urls[1], schema="legacy")
    _set_cell(row, LH.page_title, utils.resolve_seo_title(product), schema="legacy")
    keyword_value = _resolve_keywords_from_tags(product.tags)
    _set_cell(row, LH.search_keywords, keyword_value, schema="legacy")
    _set_cell(row, LH.meta_keywords, keyword_value, schema="legacy")
    _set_cell(row, LH.meta_description, utils.resolve_seo_description(product), schema="legacy")
    _set_cell(row, LH.product_condition, "New", schema="legacy")
    _set_cell(row, LH.product_url, _resolve_product_url_slug(product), schema="legacy")
    utils.apply_platform_unmapped_fields_to_row(
        row,
        product,
        platform="bigcommerce",
        canonical_headers=_BIGCOMMERCE_LEGACY_CANONICAL_HEADERS,
    )
    if variants:
        utils.apply_platform_unmapped_fields_to_row(
            row,
            product,
            platform="bigcommerce",
            canonical_headers=_BIGCOMMERCE_LEGACY_CANONICAL_HEADERS,
            variant=variants[0],
        )
    return [row]


def _product_to_bigcommerce_modern_rows(
    product: Product,
    *,
    publish: bool | None = None,
    weight_unit: str,
) -> list[dict[str, str]]:
    is_visible = utils.resolve_product_visibility(product, publish_override=publish)
    variants = utils.resolve_variants(product)
    option_names = _resolve_option_names(product, variants)
    is_variable = _is_variable_product(product, variants, option_names)
    has_inventory = _has_any_inventory_quantity(variants)
    inventory_mode = _resolve_inventory_mode(is_variable=is_variable, has_inventory=has_inventory)
    parent_sku = _resolve_parent_sku(product, variants, is_variable=is_variable)

    rows: list[dict[str, str]] = []

    first_variant = variants[0] if variants else None
    keyword_value = _resolve_keywords_from_tags(product.tags)
    product_row = _empty_row()
    _set_cell(product_row, MH.item, "Product", schema="modern")
    _set_cell(
        product_row, MH.type, "digital" if product.is_digital else "physical", schema="modern"
    )
    _set_cell(product_row, MH.name, product.title or "", schema="modern")
    _set_cell(product_row, MH.description, product.description or "", schema="modern")
    _set_cell(product_row, MH.sku, parent_sku, schema="modern")
    _set_cell(product_row, MH.price, _resolve_price(product, first_variant), schema="modern")
    _set_cell(product_row, MH.categories, _resolve_modern_categories(product), schema="modern")
    _set_cell(
        product_row,
        MH.weight,
        _require_weight(
            _resolve_product_weight_grams(product, variants),
            is_digital=product.is_digital,
            weight_unit=weight_unit,
        ),
        schema="modern",
    )
    _set_cell(product_row, MH.inventory_tracking, inventory_mode, schema="modern")
    _set_cell(
        product_row,
        MH.current_stock,
        _resolve_stock_for_product_row(variants, inventory_mode=inventory_mode),
        schema="modern",
    )
    _set_cell(product_row, MH.low_stock, "0", schema="modern")
    _set_cell(product_row, MH.product_url, _resolve_product_url_slug(product), schema="modern")
    _set_cell(
        product_row, MH.meta_description, utils.resolve_seo_description(product), schema="modern"
    )
    _set_cell(product_row, MH.search_keywords, keyword_value, schema="modern")
    _set_cell(product_row, MH.meta_keywords, keyword_value, schema="modern")
    _set_cell(
        product_row,
        MH.free_shipping,
        "TRUE" if not product.requires_shipping else "FALSE",
        schema="modern",
    )
    _set_cell(product_row, MH.is_visible, "TRUE" if is_visible else "FALSE", schema="modern")
    _set_cell(product_row, MH.is_featured, "FALSE", schema="modern")
    _set_cell(product_row, MH.tax_class, "0", schema="modern")
    _set_cell(product_row, MH.product_condition, "New", schema="modern")
    _set_cell(product_row, MH.show_product_condition, "FALSE", schema="modern")
    _set_cell(product_row, MH.sort_order, "0", schema="modern")
    utils.apply_platform_unmapped_fields_to_row(
        product_row,
        product,
        platform="bigcommerce",
        canonical_headers=_BIGCOMMERCE_MODERN_CANONICAL_HEADERS,
    )
    rows.append(product_row)

    if is_variable:
        for index, variant in enumerate(variants, start=1):
            variant_row = _empty_row()
            variant_option_values = utils.resolve_variant_option_map(product, variant)
            _set_cell(variant_row, MH.item, "Variant", schema="modern")
            _set_cell(
                variant_row,
                MH.sku,
                _resolve_variant_sku(parent_sku, variant, index=index),
                schema="modern",
            )
            _set_cell(variant_row, MH.price, _resolve_price(product, variant), schema="modern")
            _set_cell(
                variant_row,
                MH.current_stock,
                _resolve_stock_for_variant_row(variant),
                schema="modern",
            )
            _set_cell(variant_row, MH.low_stock, "0", schema="modern")
            _set_cell(
                variant_row,
                MH.free_shipping,
                "TRUE" if not product.requires_shipping else "FALSE",
                schema="modern",
            )
            _set_cell(
                variant_row, MH.is_visible, "TRUE" if is_visible else "FALSE", schema="modern"
            )
            _set_cell(variant_row, MH.show_product_condition, "FALSE", schema="modern")
            _set_cell(
                variant_row,
                MH.options,
                _build_variant_options_value(
                    variant,
                    option_names,
                    index=index,
                    values_by_name=variant_option_values,
                ),
                schema="modern",
            )
            _set_cell(
                variant_row,
                MH.variant_image_url,
                _normalize_image_url(utils.resolve_variant_image_url(variant)),
                schema="modern",
            )
            utils.apply_platform_unmapped_fields_to_row(
                variant_row,
                product,
                platform="bigcommerce",
                canonical_headers=_BIGCOMMERCE_MODERN_CANONICAL_HEADERS,
                variant=variant,
            )
            rows.append(variant_row)

    product_images = utils.ordered_unique(
        [
            url
            for url in (
                _normalize_image_url(image) for image in utils.resolve_product_image_urls(product)
            )
            if url
        ]
    )
    for image_index, image_url in enumerate(product_images, start=1):
        image_row = _empty_row()
        _set_cell(image_row, MH.item, "Image", schema="modern")
        _set_cell(image_row, MH.image_url_import, image_url, schema="modern")
        _set_cell(
            image_row,
            MH.image_is_thumbnail,
            "TRUE" if image_index == 1 else "FALSE",
            schema="modern",
        )
        _set_cell(image_row, MH.image_sort_order, str(image_index - 1), schema="modern")
        rows.append(image_row)

    if not is_variable and first_variant is not None:
        # For simple products with a variant-level image source, place it on Variant Image URL.
        _set_cell(
            rows[0],
            MH.variant_image_url,
            _normalize_image_url(utils.resolve_variant_image_url(first_variant)),
            schema="modern",
        )

    return rows


def product_to_bigcommerce_rows(
    product: Product,
    *,
    publish: bool | None = None,
    csv_format: BigCommerceCsvFormat = "modern",
    weight_unit: str = "kg",
) -> list[dict[str, str]]:
    resolved_weight_unit = resolve_weight_unit("bigcommerce", weight_unit)
    if csv_format == "modern":
        return _product_to_bigcommerce_modern_rows(
            product,
            publish=publish,
            weight_unit=resolved_weight_unit,
        )
    if csv_format == "legacy":
        return _product_to_bigcommerce_legacy_rows(
            product,
            publish=publish,
            weight_unit=resolved_weight_unit,
        )
    raise ValueError("csv_format must be one of: modern, legacy")


def product_to_bigcommerce_csv(
    product: Product,
    *,
    publish: bool | None = None,
    csv_format: BigCommerceCsvFormat = "modern",
    weight_unit: str = "kg",
) -> tuple[str, str]:
    rows = product_to_bigcommerce_rows(
        product,
        publish=publish,
        csv_format=csv_format,
        weight_unit=weight_unit,
    )
    columns = BIGCOMMERCE_COLUMNS if csv_format == "modern" else BIGCOMMERCE_LEGACY_COLUMNS
    return utils.dict_rows_to_csv(rows, columns), utils.make_export_filename("bigcommerce")
