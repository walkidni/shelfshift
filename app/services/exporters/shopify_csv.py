import re
from urllib.parse import urlparse

from slugify import slugify

from app.models import Product, Variant
from . import utils

SHOPIFY_COLUMNS: list[str] = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Type",
    "Tags",
    "Published",
    "Status",
    "Option1 Name",
    "Option1 Value",
    "Option2 Name",
    "Option2 Value",
    "Option3 Name",
    "Option3 Value",
    "Variant SKU",
    "Variant Grams",
    "Variant Inventory Tracker",
    "Variant Inventory Qty",
    "Variant Inventory Policy",
    "Variant Fulfillment Service",
    "Variant Price",
    "Variant Requires Shipping",
    "Variant Taxable",
    "Image Src",
    "Image Position",
    "Image Alt Text",
    "Variant Image",
    "Variant Weight Unit",
]

_HANDLE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHOPIFY_SUPPORTED_IMAGE_EXTENSIONS = (".gif", ".jpeg", ".jpg", ".png", ".webp", ".heic")
# Fallback used only when a non-empty source image URL is not Shopify-compatible.
SHOPIFY_DEFAULT_IMAGE_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/No_image_available.svg/"
    "1024px-No_image_available.svg.png"
)


def _empty_row() -> dict[str, str]:
    return {column: "" for column in SHOPIFY_COLUMNS}


def _format_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _format_grams(value: float | None) -> str:
    if value is None:
        return ""
    return str(max(0, int(round(value))))


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


def product_to_shopify_rows(product: Product, *, publish: bool) -> list[dict[str, str]]:
    handle = _resolve_handle(product)
    option_names = _resolve_option_names(product)
    image_alt_text = (product.title or "").strip()
    product_images = _resolve_shopify_product_images(utils.resolve_product_image_urls(product))
    rows: list[dict[str, str]] = []
    variants = utils.resolve_variants(product)

    for index, variant in enumerate(variants):
        row = _empty_row()
        variant_option_values = utils.resolve_variant_option_map(product, variant)
        row["Handle"] = handle
        row["Variant SKU"] = str(variant.sku or variant.id or "")
        row["Variant Price"] = _resolve_price(product, variant)
        row["Variant Inventory Policy"] = "deny"
        row["Variant Fulfillment Service"] = "manual"
        row["Variant Requires Shipping"] = _format_bool(bool(product.requires_shipping and not product.is_digital))
        row["Variant Taxable"] = _format_bool(not product.is_digital)
        row["Variant Image"] = _resolve_shopify_image_url(utils.resolve_variant_image_url(variant))

        grams = _format_grams(utils.resolve_weight_grams(product, variant))
        if grams:
            row["Variant Grams"] = grams
            row["Variant Weight Unit"] = "g"

        qty = _format_inventory_qty(utils.resolve_variant_inventory_quantity(variant))
        if qty:
            row["Variant Inventory Tracker"] = "shopify"
            row["Variant Inventory Qty"] = qty

        for option_index, option_name in enumerate(option_names, start=1):
            option_value = ""
            if option_name == "Title" and not variant_option_values:
                option_value = "Default Title"
            else:
                option_value = str(variant_option_values.get(option_name) or "")
            row[f"Option{option_index} Name"] = option_name
            row[f"Option{option_index} Value"] = option_value

        if index == 0:
            row["Title"] = product.title or ""
            row["Body (HTML)"] = product.description or ""
            row["Vendor"] = product.vendor or product.brand or ""
            row["Type"] = utils.resolve_primary_category(product)
            row["Tags"] = _resolve_tags(product)
            row["Published"] = _format_bool(publish)
            row["Status"] = "active" if publish else "draft"
            if product_images:
                row["Image Src"] = product_images[0]
                row["Image Position"] = "1"
                row["Image Alt Text"] = image_alt_text

        rows.append(row)

    for image_position, image_url in enumerate(product_images[1:], start=2):
        row = _empty_row()
        row["Handle"] = handle
        row["Image Src"] = image_url
        row["Image Position"] = str(image_position)
        row["Image Alt Text"] = image_alt_text
        rows.append(row)

    return rows


def product_to_shopify_csv(product: Product, *, publish: bool) -> tuple[str, str]:
    rows = product_to_shopify_rows(product, publish=publish)
    return utils.dict_rows_to_csv(rows, SHOPIFY_COLUMNS), utils.make_export_filename("shopify")
