import re
from typing import Literal
from slugify import slugify

from app.models import Product, Variant
from . import utils

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
    "Product ID",
    "Product Type",
    "Code",
    "Name",
    "Brand",
    "Description",
    "Cost Price",
    "Retail Price",
    "Sale Price",
    "Calculated Price",
    "Fixed Shipping Price",
    "Free Shipping",
    "Warranty",
    "Weight",
    "Width",
    "Height",
    "Depth",
    "Allow Purchases",
    "Product Visible",
    "Product Availability",
    "Product Inventoried",
    "Stock Level",
    "Low Stock Level",
    "Date Added",
    "Date Modified",
    "Category Details",
    "Images",
    "Page Title",
    "META Keywords",
    "META Description",
    "Product Condition",
    "Product URL",
    "Redirect Old URL?",
    "Product Tax Code",
    "Product Custom Fields",
]

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
    return {column: "" for column in BIGCOMMERCE_COLUMNS}


def _empty_legacy_row() -> dict[str, str]:
    return {column: "" for column in BIGCOMMERCE_LEGACY_COLUMNS}


def _format_price(value: float | None) -> str:
    return utils.format_number(value, decimals=6) if value is not None else ""


def _format_weight_kg(value: float | None) -> str:
    if value is None:
        return ""
    try:
        kilograms = float(value) / 1000.0
    except (TypeError, ValueError):
        return ""
    return utils.format_number(kilograms, decimals=6)


def _format_weight_kg_legacy(value: float | None) -> str:
    if value is None:
        return ""
    try:
        kilograms = float(value) / 1000.0
    except (TypeError, ValueError):
        return ""
    return utils.format_number(kilograms, decimals=4)


def _require_weight_kg(value: float | None, *, is_digital: bool) -> str:
    if is_digital:
        return ""
    formatted = _format_weight_kg(value)
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


def _is_variable_product(product: Product, variants: list[Variant], option_names: list[str]) -> bool:
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
    return utils.resolve_primary_category(product)


def _resolve_legacy_images(product: Product) -> str:
    urls = utils.ordered_unique([
        url for url in (_normalize_image_url(image) for image in utils.resolve_product_image_urls(product)) if url
    ])
    return "|".join(f"Product Image URL: {url}" for url in urls)


def _product_to_bigcommerce_legacy_rows(product: Product, *, publish: bool) -> list[dict[str, str]]:
    variants = utils.resolve_variants(product)
    option_names = _resolve_option_names(product, variants)
    is_variable = _is_variable_product(product, variants, option_names)
    has_inventory = _has_any_inventory_quantity(variants)
    inventory_mode = _resolve_inventory_mode(is_variable=is_variable, has_inventory=has_inventory)
    parent_sku = _resolve_parent_sku(product, variants, is_variable=is_variable)
    first_variant = variants[0] if variants else None

    row = _empty_legacy_row()
    row["Product ID"] = str(product.source.id or "")
    row["Product Type"] = "P"
    row["Code"] = parent_sku
    row["Name"] = product.title or ""
    row["Brand"] = product.brand or ""
    row["Description"] = product.description or ""
    row["Calculated Price"] = _resolve_price(product, first_variant)
    row["Fixed Shipping Price"] = "0.0000"
    row["Free Shipping"] = "Y" if not product.requires_shipping else "N"
    row["Weight"] = _format_weight_kg_legacy(_resolve_product_weight_grams(product, variants))
    row["Allow Purchases"] = "Y"
    row["Product Visible"] = "Y" if publish else "N"
    row["Product Inventoried"] = "Y" if inventory_mode != _INVENTORY_NONE else "N"
    row["Stock Level"] = _resolve_stock_for_product_row(variants, inventory_mode=inventory_mode)
    row["Low Stock Level"] = "0"
    row["Category Details"] = _resolve_category_details(utils.resolve_primary_category(product))
    row["Images"] = _resolve_legacy_images(product)
    row["Page Title"] = utils.resolve_seo_title(product)
    keyword_value = _resolve_keywords_from_tags(product.tags)
    row["META Keywords"] = keyword_value
    row["META Description"] = utils.resolve_seo_description(product)
    row["Product Condition"] = "New"
    row["Product URL"] = _resolve_product_url_slug(product)
    return [row]


def _product_to_bigcommerce_modern_rows(product: Product, *, publish: bool) -> list[dict[str, str]]:
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
    product_row["Item"] = "Product"
    product_row["Type"] = "digital" if product.is_digital else "physical"
    product_row["Name"] = product.title or ""
    product_row["Description"] = product.description or ""
    product_row["SKU"] = parent_sku
    product_row["Price"] = _resolve_price(product, first_variant)
    product_row["Categories"] = _resolve_modern_categories(product)
    product_row["Weight"] = _require_weight_kg(
        _resolve_product_weight_grams(product, variants),
        is_digital=product.is_digital,
    )
    product_row["Inventory Tracking"] = inventory_mode
    product_row["Current Stock"] = _resolve_stock_for_product_row(variants, inventory_mode=inventory_mode)
    product_row["Low Stock"] = "0"
    product_row["Product URL"] = _resolve_product_url_slug(product)
    product_row["Meta Description"] = utils.resolve_seo_description(product)
    product_row["Search Keywords"] = keyword_value
    product_row["Meta Keywords"] = keyword_value
    product_row["Free Shipping"] = "TRUE" if not product.requires_shipping else "FALSE"
    product_row["Is Visible"] = "TRUE" if publish else "FALSE"
    product_row["Is Featured"] = "FALSE"
    product_row["Tax Class"] = "0"
    product_row["Product Condition"] = "New"
    product_row["Show Product Condition"] = "FALSE"
    product_row["Sort Order"] = "0"
    rows.append(product_row)

    if is_variable:
        for index, variant in enumerate(variants, start=1):
            variant_row = _empty_row()
            variant_option_values = utils.resolve_variant_option_map(product, variant)
            variant_row["Item"] = "Variant"
            variant_row["SKU"] = _resolve_variant_sku(parent_sku, variant, index=index)
            variant_row["Price"] = _resolve_price(product, variant)
            variant_row["Current Stock"] = _resolve_stock_for_variant_row(variant)
            variant_row["Low Stock"] = "0"
            variant_row["Free Shipping"] = "TRUE" if not product.requires_shipping else "FALSE"
            variant_row["Is Visible"] = "TRUE" if publish else "FALSE"
            variant_row["Show Product Condition"] = "FALSE"
            variant_row["Options"] = _build_variant_options_value(
                variant,
                option_names,
                index=index,
                values_by_name=variant_option_values,
            )
            variant_row["Variant Image URL"] = _normalize_image_url(utils.resolve_variant_image_url(variant))
            rows.append(variant_row)

    product_images = utils.ordered_unique([
        url for url in (_normalize_image_url(image) for image in utils.resolve_product_image_urls(product)) if url
    ])
    for image_index, image_url in enumerate(product_images, start=1):
        image_row = _empty_row()
        image_row["Item"] = "Image"
        image_row["Image URL (Import)"] = image_url
        image_row["Image is Thumbnail"] = "TRUE" if image_index == 1 else "FALSE"
        image_row["Image Sort Order"] = str(image_index - 1)
        rows.append(image_row)

    if not is_variable and first_variant is not None:
        # For simple products with a variant-level image source, place it on Variant Image URL.
        rows[0]["Variant Image URL"] = _normalize_image_url(utils.resolve_variant_image_url(first_variant))

    return rows


def product_to_bigcommerce_rows(
    product: Product,
    *,
    publish: bool,
    csv_format: BigCommerceCsvFormat = "modern",
) -> list[dict[str, str]]:
    if csv_format == "modern":
        return _product_to_bigcommerce_modern_rows(product, publish=publish)
    if csv_format == "legacy":
        return _product_to_bigcommerce_legacy_rows(product, publish=publish)
    raise ValueError("csv_format must be one of: modern, legacy")


def product_to_bigcommerce_csv(
    product: Product,
    *,
    publish: bool,
    csv_format: BigCommerceCsvFormat = "modern",
) -> tuple[str, str]:
    rows = product_to_bigcommerce_rows(product, publish=publish, csv_format=csv_format)
    columns = BIGCOMMERCE_COLUMNS if csv_format == "modern" else BIGCOMMERCE_LEGACY_COLUMNS
    return utils.dict_rows_to_csv(rows, columns), utils.make_export_filename("bigcommerce")
