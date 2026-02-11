import re

from slugify import slugify

from ..importer import ProductResult, Variant
from . import utils

# BigCommerce Modern Product Import/Export (v3) row model.
BIGCOMMERCE_COLUMNS: list[str] = [
    "Item Type",
    "ID",
    "Type",
    "Name",
    "Description",
    "SKU",
    "Price",
    "Weight",
    "Inventory",
    "Options",
    "Variant Image URL",
    "Image URL (Import)",
    "Image Is Thumbnail?",
]

_PLATFORM_TOKEN = {
    "shopify": "SH",
    "amazon": "AMZ",
    "aliexpress": "AE",
    "squarespace": "SQ",
    "woocommerce": "WC",
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_INVENTORY_NONE = "none"
_INVENTORY_PRODUCT = "product"
_INVENTORY_VARIANT = "variant"


def _empty_row() -> dict[str, str]:
    return {column: "" for column in BIGCOMMERCE_COLUMNS}


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


def _resolve_price(product: ProductResult, variant: Variant | None = None) -> str:
    if variant and variant.price_amount is not None:
        return _format_price(variant.price_amount)
    if isinstance(product.price, dict):
        amount = product.price.get("amount")
        if isinstance(amount, (int, float)):
            return _format_price(float(amount))
    return ""


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


def _resolve_inventory_qty(variant: Variant) -> str:
    if variant.inventory_quantity is None:
        return ""
    try:
        return str(max(0, int(variant.inventory_quantity)))
    except (TypeError, ValueError):
        return ""


def _has_any_inventory_quantity(variants: list[Variant]) -> bool:
    return any(_resolve_inventory_qty(variant) != "" for variant in variants)


def _resolve_option_names(product: ProductResult, variants: list[Variant]) -> list[str]:
    option_names = utils.ordered_unique((product.options or {}).keys())
    for variant in variants:
        for option_name in utils.ordered_unique((variant.options or {}).keys()):
            if option_name in option_names:
                continue
            option_names.append(option_name)
    return option_names


def _is_variable_product(product: ProductResult, variants: list[Variant], option_names: list[str]) -> bool:
    if len(variants) > 1:
        return True
    if option_names:
        return True
    for values in (product.options or {}).values():
        if isinstance(values, (list, tuple, set)) and len(utils.ordered_unique(str(v) for v in values)) > 1:
            return True
    return False


def _fallback_variant_option_value(variant: Variant, index: int) -> str:
    return str(variant.title or variant.sku or variant.id or f"Variant {index}")


def _resolve_variant_options(option_names: list[str], variant: Variant, *, index: int) -> str:
    if not option_names:
        value = _fallback_variant_option_value(variant, index)
        return f"Option={value}"

    pairs: list[str] = []
    for option_name in option_names:
        option_value = str((variant.options or {}).get(option_name) or "")
        if option_value:
            pairs.append(f"{option_name}={option_value}")
    return ",".join(pairs)


def _normalize_image_url(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        return f"https:{raw}"
    if raw.startswith(("http://", "https://")):
        return raw
    return ""


def _resolve_inventory_mode(*, is_variable: bool, has_inventory: bool) -> str:
    if not has_inventory:
        return _INVENTORY_NONE
    if is_variable:
        return _INVENTORY_VARIANT
    return _INVENTORY_PRODUCT


def product_to_bigcommerce_rows(product: ProductResult, *, publish: bool) -> list[dict[str, str]]:
    _ = publish  # Reserved for future modern-v3 visibility field mapping.
    variants = utils.resolve_variants(product)
    option_names = _resolve_option_names(product, variants)
    is_variable = _is_variable_product(product, variants, option_names)
    has_inventory = _has_any_inventory_quantity(variants)
    parent_sku = _resolve_parent_sku(product, variants, is_variable=is_variable)

    rows: list[dict[str, str]] = []

    first_variant = variants[0] if variants else None
    product_row = _empty_row()
    product_row["Item Type"] = "Product"
    product_row["Type"] = "digital" if product.is_digital else "physical"
    product_row["Name"] = product.title or ""
    product_row["Description"] = product.description or ""
    product_row["SKU"] = parent_sku
    product_row["Price"] = _resolve_price(product, first_variant)
    product_row["Weight"] = _format_weight_kg(first_variant.weight if first_variant else product.weight)
    product_row["Inventory"] = _resolve_inventory_mode(is_variable=is_variable, has_inventory=has_inventory)
    rows.append(product_row)

    if is_variable:
        for index, variant in enumerate(variants, start=1):
            variant_row = _empty_row()
            variant_row["Item Type"] = "Variant"
            variant_row["Name"] = product.title or ""
            variant_row["Description"] = _strip_html(product.description)
            variant_row["SKU"] = _resolve_variant_sku(parent_sku, variant, index=index)
            variant_row["Price"] = _resolve_price(product, variant)
            variant_row["Weight"] = _format_weight_kg(variant.weight if variant.weight is not None else product.weight)
            variant_row["Options"] = _resolve_variant_options(option_names, variant, index=index)
            variant_row["Variant Image URL"] = _normalize_image_url(variant.image)
            rows.append(variant_row)

    product_images = utils.ordered_unique(
        [url for url in (_normalize_image_url(image) for image in (product.images or [])) if url]
    )
    for image_index, image_url in enumerate(product_images, start=1):
        image_row = _empty_row()
        image_row["Item Type"] = "Image"
        image_row["Image URL (Import)"] = image_url
        image_row["Image Is Thumbnail?"] = "TRUE" if image_index == 1 else "FALSE"
        rows.append(image_row)

    if not is_variable and first_variant is not None:
        # For simple products with a variant-level image source, place it on Variant Image URL.
        rows[0]["Variant Image URL"] = _normalize_image_url(first_variant.image)

    return rows


def product_to_bigcommerce_csv(product: ProductResult, *, publish: bool) -> tuple[str, str]:
    rows = product_to_bigcommerce_rows(product, publish=publish)
    return utils.dict_rows_to_csv(rows, BIGCOMMERCE_COLUMNS), utils.make_export_filename("bigcommerce")
