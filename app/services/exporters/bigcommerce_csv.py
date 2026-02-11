import re

from slugify import slugify

from ..importer import ProductResult, Variant
from . import utils

_BIGCOMMERCE_HEADER = (
    "Item Type,Product ID,Product Name,Product Type,Product Code/SKU,Bin Picking Number,Brand Name,Option Set,"
    "Option Set Align,Product Description,Price,Cost Price,Retail Price,Sale Price,Fixed Shipping Cost,Free Shipping,"
    "Product Warranty,Product Weight,Product Width,Product Height,Product Depth,Allow Purchases?,Product Visible?,"
    "Product Availability,Track Inventory,Current Stock Level,Low Stock Level,Category,Product Image ID - 1,"
    "Product Image File - 1,Product Image Description - 1,Product Image Is Thumbnail - 1,Product Image Sort - 1,"
    "Product Image ID - 2,Product Image File - 2,Product Image Description - 2,Product Image Is Thumbnail - 2,"
    "Product Image Sort - 2,Search Keywords,Page Title,Meta Keywords,Meta Description,MYOB Asset Acct,"
    "MYOB Income Acct,MYOB Expense Acct,Product Condition,Show Product Condition?,Event Date Required?,Event Date Name,"
    "Event Date Is Limited?,Event Date Start Date,Event Date End Date,Sort Order,Product Tax Class,Product UPC/EAN,"
    "Stop Processing Rules,Product URL,Redirect Old URL?,Global Trade Item Number,Manufacturer Part Number"
)

BIGCOMMERCE_COLUMNS: list[str] = _BIGCOMMERCE_HEADER.split(",")

_PLATFORM_TOKEN = {
    "shopify": "SH",
    "amazon": "AMZ",
    "aliexpress": "AE",
    "squarespace": "SQ",
    "woocommerce": "WC",
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _empty_row() -> dict[str, str]:
    return {column: "" for column in BIGCOMMERCE_COLUMNS}


def _format_yes_no(value: bool) -> str:
    return "Y" if value else "N"


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


def _strip_html(value: str | None) -> str:
    cleaned = _HTML_TAG_RE.sub(" ", value or "")
    return " ".join(cleaned.split())


def _resolve_tags(product: ProductResult) -> str:
    tags = sorted(utils.ordered_unique(product.tags or []), key=str.lower)
    return ",".join(tags)


def _resolve_option_names(product: ProductResult, variants: list[Variant]) -> list[str]:
    option_names = utils.ordered_unique((product.options or {}).keys())
    for variant in variants:
        for option_name in utils.ordered_unique((variant.options or {}).keys()):
            if option_name in option_names:
                continue
            option_names.append(option_name)
    return option_names


def _resolve_price(product: ProductResult, variant: Variant | None = None) -> str:
    if variant and variant.price_amount is not None:
        return _format_price(variant.price_amount)
    if isinstance(product.price, dict):
        amount = product.price.get("amount")
        if isinstance(amount, (int, float)):
            return _format_price(float(amount))
    return ""


def _resolve_option_set(option_names: list[str]) -> str:
    return ", ".join(option_names)


def _resolve_product_key(product: ProductResult) -> str:
    for candidate in (product.id, product.slug, product.title):
        key = slugify(str(candidate or ""), separator="-")
        if key:
            return key
    return "item"


def _platform_token(platform: str | None) -> str:
    return _PLATFORM_TOKEN.get((platform or "").strip().lower(), "SRC")


def _resolve_parent_sku(product: ProductResult, variants: list[Variant], *, is_variable: bool) -> str:
    if not is_variable and variants:
        sku = (variants[0].sku or "").strip()
        if sku:
            return sku
    return f"{_platform_token(product.platform)}-{_resolve_product_key(product)}".upper()


def _resolve_variant_sku(parent_sku: str, variant: Variant, *, index: int) -> str:
    return str(variant.sku or variant.id or f"{parent_sku}-{index}")


def _fallback_variant_option_value(variant: Variant, index: int) -> str:
    return str(variant.title or variant.sku or variant.id or f"Variant {index}")


def _resolve_variant_name(
    product: ProductResult,
    variant: Variant,
    option_names: list[str],
    *,
    index: int,
) -> str:
    product_title = product.title or "Product"
    parts: list[str] = []
    for option_name in option_names:
        option_value = str((variant.options or {}).get(option_name) or "")
        if option_value:
            parts.append(f"[S]{option_name}={option_value}[/S]")

    if not parts and len(option_names) == 0:
        fallback = _fallback_variant_option_value(variant, index)
        if fallback and fallback != product_title:
            parts.append(f"[S]Option={fallback}[/S]")

    if not parts:
        return product_title
    return f"{product_title} {' '.join(parts)}"


def _resolve_inventory_qty(variant: Variant) -> str:
    if variant.inventory_quantity is None:
        return ""
    try:
        return str(max(0, int(variant.inventory_quantity)))
    except (TypeError, ValueError):
        return ""


def _is_variable_product(product: ProductResult, variants: list[Variant], option_names: list[str]) -> bool:
    if len(variants) > 1:
        return True
    if option_names:
        return True
    for values in (product.options or {}).values():
        if isinstance(values, (list, tuple, set)) and len(utils.ordered_unique(str(v) for v in values)) > 1:
            return True
    return False


def _resolve_product_url(product: ProductResult) -> str:
    slug = slugify(product.slug or product.title or "", separator="-")
    return slug


def _set_product_images(row: dict[str, str], product: ProductResult) -> None:
    images = utils.ordered_unique(product.images or [])
    if not images:
        return
    row["Product Image File - 1"] = images[0]
    row["Product Image Description - 1"] = (product.title or "").strip()
    row["Product Image Is Thumbnail - 1"] = "TRUE"
    row["Product Image Sort - 1"] = "0"
    if len(images) > 1:
        row["Product Image File - 2"] = images[1]
        row["Product Image Description - 2"] = (product.title or "").strip()
        row["Product Image Is Thumbnail - 2"] = "FALSE"
        row["Product Image Sort - 2"] = "1"


def product_to_bigcommerce_rows(product: ProductResult, *, publish: bool) -> list[dict[str, str]]:
    variants = utils.resolve_variants(product)
    option_names = _resolve_option_names(product, variants)
    option_set = _resolve_option_set(option_names)
    is_variable = _is_variable_product(product, variants, option_names)
    parent_sku = _resolve_parent_sku(product, variants, is_variable=is_variable)
    tags = _resolve_tags(product)
    meta_description = product.meta_description or _strip_html(product.description)

    rows: list[dict[str, str]] = []

    first_variant = variants[0] if variants else None
    product_row = _empty_row()
    product_row["Item Type"] = "Product"
    product_row["Product Name"] = product.title or ""
    product_row["Product Code/SKU"] = parent_sku
    product_row["Brand Name"] = product.vendor or product.brand or ""
    product_row["Option Set"] = option_set
    product_row["Product Description"] = product.description or ""
    product_row["Price"] = _resolve_price(product, first_variant)
    product_row["Product Weight"] = _format_weight_kg(first_variant.weight if first_variant else product.weight)
    product_row["Allow Purchases?"] = "Y"
    product_row["Product Visible?"] = _format_yes_no(publish)
    product_row["Track Inventory"] = "N"
    product_row["Category"] = (product.category or "").strip()
    product_row["Search Keywords"] = tags
    product_row["Page Title"] = product.meta_title or product.title or ""
    product_row["Meta Keywords"] = tags
    product_row["Meta Description"] = meta_description
    product_row["Sort Order"] = "0"
    product_row["Product URL"] = _resolve_product_url(product)
    product_row["Redirect Old URL?"] = "N"
    _set_product_images(product_row, product)

    if not is_variable and first_variant is not None:
        qty = _resolve_inventory_qty(first_variant)
        if qty:
            product_row["Track Inventory"] = "Y"
            product_row["Current Stock Level"] = qty

    rows.append(product_row)

    if not is_variable:
        return rows

    for index, variant in enumerate(variants, start=1):
        variant_row = _empty_row()
        variant_row["Item Type"] = "SKU"
        variant_row["Product Name"] = _resolve_variant_name(product, variant, option_names, index=index)
        variant_row["Product Code/SKU"] = _resolve_variant_sku(parent_sku, variant, index=index)
        variant_row["Brand Name"] = product.vendor or product.brand or ""
        variant_row["Option Set"] = option_set
        variant_row["Price"] = _resolve_price(product, variant)
        variant_row["Allow Purchases?"] = "Y"
        variant_row["Product Visible?"] = _format_yes_no(publish)
        variant_row["Product Weight"] = _format_weight_kg(variant.weight if variant.weight is not None else product.weight)
        variant_row["Sort Order"] = str(index)
        if variant.image:
            variant_row["Product Image File - 1"] = variant.image
            variant_row["Product Image Description - 1"] = variant.title or product.title or ""

        qty = _resolve_inventory_qty(variant)
        if qty:
            variant_row["Track Inventory"] = "Y"
            variant_row["Current Stock Level"] = qty
        else:
            variant_row["Track Inventory"] = "N"

        rows.append(variant_row)

    return rows


def product_to_bigcommerce_csv(product: ProductResult, *, publish: bool) -> tuple[str, str]:
    rows = product_to_bigcommerce_rows(product, publish=publish)
    return utils.dict_rows_to_csv(rows, BIGCOMMERCE_COLUMNS), utils.make_export_filename("bigcommerce")
