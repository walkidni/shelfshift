import re
from urllib.parse import urlparse

from slugify import slugify

from ...canonical import Product, Variant
from ..shared import utils
from ..shared.weight_units import resolve_weight_unit

SHOPIFY_COLUMNS: list[str] = [
    "Title",
    "URL handle",
    "Description",
    "Vendor",
    "Product category",
    "Type",
    "Tags",
    "Published on online store",
    "Status",
    "SKU",
    "Barcode",
    "Option1 name",
    "Option1 value",
    "Option1 Linked To",
    "Option2 name",
    "Option2 value",
    "Option2 Linked To",
    "Option3 name",
    "Option3 value",
    "Option3 Linked To",
    "Price",
    "Compare-at price",
    "Cost per item",
    "Charge tax",
    "Tax code",
    "Unit price total measure",
    "Unit price total measure unit",
    "Unit price base measure",
    "Unit price base measure unit",
    "Inventory tracker",
    "Inventory quantity",
    "Continue selling when out of stock",
    "Weight value (grams)",
    "Weight unit for display",
    "Requires shipping",
    "Fulfillment service",
    "Product image URL",
    "Image position",
    "Image alt text",
    "Variant image URL",
    "Gift card",
    "SEO title",
    "SEO description",
    "Color (product.metafields.shopify.color-pattern)",
    "Google Shopping / Google product category",
    "Google Shopping / Gender",
    "Google Shopping / Age group",
    "Google Shopping / Manufacturer part number (MPN)",
    "Google Shopping / Ad group name",
    "Google Shopping / Ads labels",
    "Google Shopping / Condition",
    "Google Shopping / Custom product",
    "Google Shopping / Custom label 0",
    "Google Shopping / Custom label 1",
    "Google Shopping / Custom label 2",
    "Google Shopping / Custom label 3",
    "Google Shopping / Custom label 4",
]

_HANDLE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHOPIFY_SUPPORTED_IMAGE_EXTENSIONS = (".gif", ".jpeg", ".jpg", ".png", ".webp", ".heic")
# Fallback used only when a non-empty source image URL is not Shopify-compatible.
SHOPIFY_DEFAULT_IMAGE_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/"
    "1024px-No_image_available.svg.png"
)


def _empty_row() -> dict[str, str]:
    return dict.fromkeys(SHOPIFY_COLUMNS, "")


def _format_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _format_grams(value: float | None) -> str:
    if value is None:
        return ""
    return str(max(0, round(value)))


def _format_inventory_qty(value: int | None) -> str:
    if value is None:
        return ""
    try:
        return str(max(0, int(value)))
    except (TypeError, ValueError):
        return ""


def _normalize_handle(value: str) -> str:
    normalized = value.strip().lower()
    if _HANDLE_RE.fullmatch(normalized):
        return normalized
    return ""


def _resolve_handle(product: Product) -> str:
    if product.source.slug:
        handle = _normalize_handle(product.source.slug)
        if handle:
            return handle

    if product.title:
        title_handle = _normalize_handle(slugify(product.title))
        if title_handle:
            return title_handle

    fallback = slugify(f"{product.source.platform or 'product'}-{product.source.id or 'item'}")
    handle = _normalize_handle(fallback)
    return handle or "product-item"


def _resolve_option_names(product: Product) -> list[str]:
    option_names = [option.name for option in utils.resolve_option_defs(product) if option.name]
    if not option_names:
        return ["Title"]
    return option_names[:3]


def _resolve_tags(product: Product) -> str:
    tags = sorted(utils.ordered_unique(product.tags or []), key=str.lower)
    return ",".join(tags)


def _resolve_type(product: Product) -> str:
    passthrough = utils.resolve_unmapped_field(product, "shopify:type")
    if passthrough:
        return passthrough
    return utils.resolve_primary_category(product)


def _resolve_price(product: Product, variant: Variant) -> str:
    amount = utils.resolve_price_amount(product, variant)
    return utils.format_number(amount, decimals=2) if amount is not None else ""


def _is_valid_shopify_image_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    path = (parsed.path or "").strip().lower()
    if not path:
        return False
    return any(path.endswith(ext) for ext in _SHOPIFY_SUPPORTED_IMAGE_EXTENSIONS)


def _resolve_shopify_image_url(value: str | None) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    if _is_valid_shopify_image_url(candidate):
        return candidate
    return SHOPIFY_DEFAULT_IMAGE_URL


def _resolve_shopify_product_images(images: list[str] | None) -> list[str]:
    resolved = [_resolve_shopify_image_url(value) for value in (images or [])]
    non_empty = [value for value in resolved if value]
    return utils.ordered_unique(non_empty)


def product_to_shopify_rows(
    product: Product,
    *,
    publish: bool | None = None,
    weight_unit: str = "g",
) -> list[dict[str, str]]:
    resolved_weight_unit = resolve_weight_unit("shopify", weight_unit)
    is_visible = utils.resolve_product_visibility(product, publish_override=publish)
    handle = _resolve_handle(product)
    option_names = _resolve_option_names(product)
    image_alt_text = (product.title or "").strip()
    product_images = _resolve_shopify_product_images(utils.resolve_product_image_urls(product))
    rows: list[dict[str, str]] = []
    variants = utils.resolve_variants(product)

    for index, variant in enumerate(variants):
        row = _empty_row()
        variant_option_values = utils.resolve_variant_option_map(product, variant)
        row["URL handle"] = handle
        row["SKU"] = str(variant.sku or variant.id or "")
        row["Price"] = _resolve_price(product, variant)
        row["Continue selling when out of stock"] = "FALSE"
        row["Fulfillment service"] = "manual"
        row["Requires shipping"] = _format_bool(
            bool(product.requires_shipping and not product.is_digital)
        )
        row["Charge tax"] = _format_bool(not product.is_digital)
        row["Variant image URL"] = _resolve_shopify_image_url(
            utils.resolve_variant_image_url(variant)
        )
        row["Gift card"] = "FALSE"

        grams = _format_grams(utils.resolve_weight_grams(product, variant))
        if grams:
            row["Weight value (grams)"] = grams
            row["Weight unit for display"] = resolved_weight_unit

        qty = _format_inventory_qty(utils.resolve_variant_inventory_quantity(variant))
        if qty:
            row["Inventory tracker"] = "shopify"
            row["Inventory quantity"] = qty

        for option_index, option_name in enumerate(option_names, start=1):
            option_value = ""
            if option_name == "Title" and not variant_option_values:
                option_value = "Default Title"
            else:
                option_value = str(variant_option_values.get(option_name) or "")
            row[f"Option{option_index} name"] = option_name
            row[f"Option{option_index} value"] = option_value

        if index == 0:
            row["Title"] = product.title or ""
            row["Description"] = product.description or ""
            row["Vendor"] = product.vendor or product.brand or ""
            row["Product category"] = utils.resolve_primary_category(product)
            row["Type"] = _resolve_type(product)
            row["Tags"] = _resolve_tags(product)
            row["Published on online store"] = _format_bool(is_visible)
            row["Status"] = "Active" if is_visible else "Draft"
            row["SEO title"] = utils.resolve_seo_title(product)
            row["SEO description"] = utils.resolve_seo_description(product)
            if product_images:
                row["Product image URL"] = product_images[0]
                row["Image position"] = "1"
                row["Image alt text"] = image_alt_text

        rows.append(row)

    for image_position, image_url in enumerate(product_images[1:], start=2):
        row = _empty_row()
        row["URL handle"] = handle
        row["Product image URL"] = image_url
        row["Image position"] = str(image_position)
        row["Image alt text"] = image_alt_text
        rows.append(row)

    return rows


def product_to_shopify_csv(
    product: Product,
    *,
    publish: bool | None = None,
    weight_unit: str = "g",
) -> tuple[str, str]:
    rows = product_to_shopify_rows(product, publish=publish, weight_unit=weight_unit)
    return utils.dict_rows_to_csv(rows, SHOPIFY_COLUMNS), utils.make_export_filename("shopify")
