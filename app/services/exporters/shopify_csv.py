import re

from slugify import slugify

from ..importer import ProductResult, Variant
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


def _empty_row() -> dict[str, str]:
    return {column: "" for column in SHOPIFY_COLUMNS}


def _format_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _format_grams(value: float | None) -> str:
    if value is None:
        return ""
    return str(max(0, int(round(value))))


def _normalize_handle(value: str) -> str:
    normalized = value.strip().lower()
    if _HANDLE_RE.fullmatch(normalized):
        return normalized
    return ""


def _resolve_handle(product: ProductResult) -> str:
    if product.slug:
        handle = _normalize_handle(product.slug)
        if handle:
            return handle

    if product.title:
        title_handle = _normalize_handle(slugify(product.title))
        if title_handle:
            return title_handle

    fallback = slugify(f"{product.platform or 'product'}-{product.id or 'item'}")
    handle = _normalize_handle(fallback)
    return handle or "product-item"


def _resolve_option_names(product: ProductResult) -> list[str]:
    option_names = utils.ordered_unique(product.options.keys())
    if len(option_names) < 3:
        for variant in product.variants or []:
            for key in utils.ordered_unique((variant.options or {}).keys()):
                if key in option_names:
                    continue
                option_names.append(key)
                if len(option_names) == 3:
                    break
            if len(option_names) == 3:
                break

    if not option_names:
        return ["Title"]
    return option_names[:3]


def _resolve_tags(product: ProductResult) -> str:
    tags = sorted(utils.ordered_unique(product.tags or []), key=str.lower)
    return ",".join(tags)


def _resolve_price(product: ProductResult, variant: Variant) -> str:
    if variant.price_amount is not None:
        return utils.format_number(variant.price_amount, decimals=2)
    if isinstance(product.price, dict):
        amount = product.price.get("amount")
        if isinstance(amount, (int, float)):
            return utils.format_number(float(amount), decimals=2)
    return ""


def product_to_shopify_rows(product: ProductResult, *, publish: bool) -> list[dict[str, str]]:
    handle = _resolve_handle(product)
    option_names = _resolve_option_names(product)
    image_alt_text = (product.title or "").strip()
    rows: list[dict[str, str]] = []
    variants = utils.resolve_variants(product)

    for index, variant in enumerate(variants):
        row = _empty_row()
        row["Handle"] = handle
        row["Variant SKU"] = str(variant.sku or variant.id or "")
        row["Variant Price"] = _resolve_price(product, variant)
        row["Variant Fulfillment Service"] = "manual"
        row["Variant Requires Shipping"] = _format_bool(bool(product.requires_shipping and not product.is_digital))
        row["Variant Taxable"] = _format_bool(not product.is_digital)
        row["Variant Image"] = str(variant.image or "")

        weight = variant.weight if variant.weight is not None else product.weight
        grams = _format_grams(weight)
        if grams:
            row["Variant Grams"] = grams
            row["Variant Weight Unit"] = "g"

        if variant.inventory_quantity is not None:
            row["Variant Inventory Tracker"] = "shopify"
            row["Variant Inventory Qty"] = str(variant.inventory_quantity)
            row["Variant Inventory Policy"] = "deny"

        for option_index, option_name in enumerate(option_names, start=1):
            option_value = ""
            if option_name == "Title" and not (variant.options or {}):
                option_value = "Default Title"
            else:
                option_value = str((variant.options or {}).get(option_name) or "")
            row[f"Option{option_index} Name"] = option_name
            row[f"Option{option_index} Value"] = option_value

        if index == 0:
            row["Title"] = product.title or ""
            row["Body (HTML)"] = product.description or ""
            row["Vendor"] = product.vendor or product.brand or ""
            row["Type"] = product.category or ""
            row["Tags"] = _resolve_tags(product)
            row["Published"] = _format_bool(publish)
            row["Status"] = "active" if publish else "draft"
            if product.images:
                row["Image Src"] = product.images[0]
                row["Image Position"] = "1"
                row["Image Alt Text"] = image_alt_text

        rows.append(row)

    for image_position, image_url in enumerate(product.images[1:], start=2):
        row = _empty_row()
        row["Handle"] = handle
        row["Image Src"] = image_url
        row["Image Position"] = str(image_position)
        row["Image Alt Text"] = image_alt_text
        rows.append(row)

    return rows


def product_to_shopify_csv(product: ProductResult, *, publish: bool) -> tuple[str, str]:
    rows = product_to_shopify_rows(product, publish=publish)
    return utils.dict_rows_to_csv(rows, SHOPIFY_COLUMNS), utils.make_export_filename("shopify")
