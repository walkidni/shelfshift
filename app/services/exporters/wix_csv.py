import re

from slugify import slugify

from ..importer import ProductResult, Variant
from . import utils

WIX_COLUMNS: list[str] = [
    "handle",
    "fieldType",
    "name",
    "visible",
    "price",
    "sku",
    "inventory",
    "productOptionName[1]",
    "productOptionType[1]",
    "productOptionChoices[1]",
    "mediaUrl",
]

_HANDLE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _empty_row() -> dict[str, str]:
    return {column: "" for column in WIX_COLUMNS}


def _format_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


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


def _resolve_price(product: ProductResult, variant: Variant | None = None) -> str:
    if variant and variant.price_amount is not None:
        return utils.format_number(variant.price_amount, decimals=2)
    if isinstance(product.price, dict):
        amount = product.price.get("amount")
        if isinstance(amount, (int, float)):
            return utils.format_number(float(amount), decimals=2)
    return ""


def _resolve_option_name(product: ProductResult, variants: list[Variant]) -> str:
    option_names = utils.ordered_unique((product.options or {}).keys())
    if not option_names:
        for variant in variants:
            for option_name in utils.ordered_unique((variant.options or {}).keys()):
                option_names.append(option_name)
                if option_names:
                    break
            if option_names:
                break
    if option_names:
        return option_names[0]
    if len(variants) > 1:
        return "Option"
    return ""


def _fallback_option_value(variant: Variant, index: int) -> str:
    return str(variant.title or variant.sku or variant.id or f"Variant {index}")


def _resolve_product_option_choices(
    product: ProductResult,
    variants: list[Variant],
    option_name: str,
) -> str:
    if not option_name:
        return ""

    values: list[str] = []
    if option_name != "Option":
        raw_values = (product.options or {}).get(option_name, [])
        if isinstance(raw_values, (list, tuple, set)):
            values.extend(str(v) for v in raw_values)
        elif raw_values is not None:
            values.append(str(raw_values))

    for index, variant in enumerate(variants, start=1):
        if option_name == "Option":
            values.append(_fallback_option_value(variant, index))
        else:
            value = str((variant.options or {}).get(option_name) or "")
            if value:
                values.append(value)

    return ";".join(utils.ordered_unique(values))


def _resolve_variant_option_choice(option_name: str, variant: Variant, *, index: int) -> str:
    if not option_name:
        return ""
    if option_name == "Option":
        return _fallback_option_value(variant, index)
    return str((variant.options or {}).get(option_name) or "")


def product_to_wix_rows(product: ProductResult, *, publish: bool) -> list[dict[str, str]]:
    handle = _resolve_handle(product)
    variants = utils.resolve_variants(product)
    images = utils.ordered_unique(product.images or [])
    option_name = _resolve_option_name(product, variants)

    rows: list[dict[str, str]] = []

    product_row = _empty_row()
    product_row["handle"] = handle
    product_row["fieldType"] = "PRODUCT"
    product_row["name"] = product.title or ""
    product_row["visible"] = _format_bool(publish)
    product_row["price"] = _resolve_price(product, variants[0] if variants else None)
    if option_name:
        product_row["productOptionName[1]"] = option_name
        product_row["productOptionType[1]"] = "TEXT_CHOICES"
        product_row["productOptionChoices[1]"] = _resolve_product_option_choices(product, variants, option_name)
    if images:
        product_row["mediaUrl"] = images[0]
    rows.append(product_row)

    for index, variant in enumerate(variants, start=1):
        variant_row = _empty_row()
        variant_row["handle"] = handle
        variant_row["fieldType"] = "VARIANT"
        variant_row["price"] = _resolve_price(product, variant)
        variant_row["sku"] = str(variant.sku or variant.id or "")
        variant_row["inventory"] = _format_inventory_qty(variant.inventory_quantity)
        if option_name:
            variant_row["productOptionName[1]"] = option_name
            variant_row["productOptionType[1]"] = "TEXT_CHOICES"
            variant_row["productOptionChoices[1]"] = _resolve_variant_option_choice(option_name, variant, index=index)
        rows.append(variant_row)

    return rows


def product_to_wix_csv(product: ProductResult, *, publish: bool) -> tuple[str, str]:
    rows = product_to_wix_rows(product, publish=publish)
    return utils.dict_rows_to_csv(rows, WIX_COLUMNS), utils.make_export_filename("wix")
