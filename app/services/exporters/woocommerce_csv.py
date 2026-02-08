import re
from typing import Iterable

from slugify import slugify

from ..importer import ProductResult, Variant
from . import utils

WOOCOMMERCE_COLUMNS: list[str] = [
    "Type",
    "SKU",
    "Name",
    "Published",
    "Is featured?",
    "Visibility in catalog",
    "Short description",
    "Description",
    "Tax status",
    "In stock?",
    "Stock",
    "Backorders allowed?",
    "Sold individually?",
    "Weight (kg)",
    "Regular price",
    "Categories",
    "Tags",
    "Images",
    "Attribute 1 name",
    "Attribute 1 value(s)",
    "Attribute 1 visible",
    "Attribute 1 global",
    "Attribute 2 name",
    "Attribute 2 value(s)",
    "Attribute 2 visible",
    "Attribute 2 global",
    "Attribute 3 name",
    "Attribute 3 value(s)",
    "Attribute 3 visible",
    "Attribute 3 global",
    "Parent",
]

_PLATFORM_TOKEN = {
    "shopify": "SH",
    "amazon": "AMZ",
    "aliexpress": "AE",
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _empty_row() -> dict[str, str]:
    return {column: "" for column in WOOCOMMERCE_COLUMNS}


def _slug(value: str | None) -> str:
    if value is None:
        return ""
    return slugify(str(value).strip(), separator="-")


def _platform_token(platform: str | None) -> str:
    return _PLATFORM_TOKEN.get((platform or "").strip().lower(), "SRC")


def _resolve_product_key(product: ProductResult) -> str:
    for candidate in (product.id, product.slug, product.title):
        key = _slug(candidate)
        if key:
            return key
    return "item"


def _resolve_parent_sku(product: ProductResult) -> str:
    return f"{_platform_token(product.platform)}:{_resolve_product_key(product)}"


def _resolve_variant_key(variant: Variant, index: int) -> str:
    for candidate in (variant.id, variant.sku, variant.title):
        key = _slug(candidate)
        if key:
            return key
    return str(index)


def _resolve_option_names(product: ProductResult, variants: list[Variant]) -> list[str]:
    names = utils.ordered_unique((product.options or {}).keys())
    if len(names) < 3:
        for variant in variants:
            for option_name in utils.ordered_unique((variant.options or {}).keys()):
                if option_name in names:
                    continue
                names.append(option_name)
                if len(names) == 3:
                    break
            if len(names) == 3:
                break
    if not names and len(variants) > 1:
        return ["Option"]
    return names[:3]


def _fallback_option_value(variant: Variant, index: int) -> str:
    return str(variant.title or variant.sku or variant.id or f"Variant {index}")


def _resolve_parent_attribute_values(
    product: ProductResult,
    variants: list[Variant],
    option_names: list[str],
) -> dict[str, list[str]]:
    values_by_option: dict[str, list[str]] = {}
    for option_name in option_names:
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
                values.append(str((variant.options or {}).get(option_name) or ""))
        values_by_option[option_name] = utils.ordered_unique(values)
    return values_by_option


def _resolve_price(product: ProductResult, variant: Variant | None = None) -> str:
    if variant and variant.price_amount is not None:
        return utils.format_number(variant.price_amount, decimals=6)
    if isinstance(product.price, dict):
        amount = product.price.get("amount")
        if isinstance(amount, (int, float)):
            return utils.format_number(float(amount), decimals=6)
    return ""


def _resolve_weight_kg(product: ProductResult, variant: Variant | None = None) -> str:
    grams = variant.weight if variant and variant.weight is not None else product.weight
    if grams is None:
        return ""
    try:
        kg = float(grams) / 1000.0
    except (TypeError, ValueError):
        return ""
    return utils.format_number(kg, decimals=6)


def _resolve_tags(product: ProductResult) -> str:
    tags = sorted(utils.ordered_unique(product.tags or []), key=str.lower)
    return ",".join(tags)


def _resolve_images(images: Iterable[str]) -> str:
    return ",".join(utils.ordered_unique(str(image) for image in images))


def _strip_html(text: str | None) -> str:
    cleaned = _HTML_TAG_RE.sub(" ", text or "")
    return " ".join(cleaned.split())


def _resolve_short_description(product: ProductResult) -> str:
    if product.meta_description:
        return product.meta_description
    return _strip_html(product.description)


def _set_common_product_fields(row: dict[str, str], product: ProductResult, *, publish: bool) -> None:
    row["Published"] = "1" if publish else "0"
    row["Is featured?"] = "0"
    row["Visibility in catalog"] = "visible"
    row["Short description"] = _resolve_short_description(product)
    row["Description"] = product.description or ""
    row["Tax status"] = "none" if product.is_digital else "taxable"
    row["Backorders allowed?"] = "0"
    row["Sold individually?"] = "0"
    row["Categories"] = (product.category or "").strip()
    row["Tags"] = _resolve_tags(product)


def _variant_in_stock(variant: Variant) -> bool:
    if variant.inventory_quantity is not None:
        try:
            return int(variant.inventory_quantity) > 0
        except (TypeError, ValueError):
            return False
    if variant.available is not None:
        return bool(variant.available)
    return True


def _apply_stock_fields(row: dict[str, str], variant: Variant) -> None:
    if variant.inventory_quantity is not None:
        try:
            qty = max(0, int(variant.inventory_quantity))
        except (TypeError, ValueError):
            qty = 0
        row["Stock"] = str(qty)
        row["In stock?"] = "1" if qty > 0 else "0"
        return
    if variant.available is not None:
        row["In stock?"] = "1" if variant.available else "0"
        return
    row["In stock?"] = "1"


def _set_attributes(
    row: dict[str, str],
    option_names: list[str],
    values_by_option: dict[str, str],
) -> None:
    for index, option_name in enumerate(option_names, start=1):
        value = values_by_option.get(option_name, "")
        row[f"Attribute {index} name"] = option_name
        row[f"Attribute {index} value(s)"] = value
        row[f"Attribute {index} visible"] = "1"
        row[f"Attribute {index} global"] = "0"


def _is_variable_product(product: ProductResult, variants: list[Variant]) -> bool:
    if len(variants) > 1:
        return True
    for values in (product.options or {}).values():
        if isinstance(values, (list, tuple, set)):
            option_values = [str(v) for v in values]
        elif values is None:
            option_values = []
        else:
            option_values = [str(values)]
        if len(utils.ordered_unique(option_values)) > 1:
            return True
    return False


def product_to_woocommerce_rows(product: ProductResult, *, publish: bool) -> list[dict[str, str]]:
    variants = utils.resolve_variants(product)
    option_names = _resolve_option_names(product, variants)
    parent_sku = _resolve_parent_sku(product)
    images = utils.ordered_unique(product.images or [])
    parent_attribute_values = _resolve_parent_attribute_values(product, variants, option_names)
    is_variable = _is_variable_product(product, variants)

    if not is_variable:
        variant = variants[0]
        row = _empty_row()
        _set_common_product_fields(row, product, publish=publish)
        row["Type"] = "simple"
        row["SKU"] = parent_sku
        row["Name"] = product.title or ""
        row["Regular price"] = _resolve_price(product, variant)
        row["Weight (kg)"] = _resolve_weight_kg(product, variant)
        row["Images"] = _resolve_images(images or [variant.image or ""])
        _apply_stock_fields(row, variant)
        simple_values: dict[str, str] = {}
        for index, option_name in enumerate(option_names, start=1):
            if option_name == "Option":
                simple_values[option_name] = _fallback_option_value(variant, index)
            else:
                simple_values[option_name] = str((variant.options or {}).get(option_name) or "")
        _set_attributes(row, option_names, simple_values)
        return [row]

    rows: list[dict[str, str]] = []
    parent_row = _empty_row()
    _set_common_product_fields(parent_row, product, publish=publish)
    parent_row["Type"] = "variable"
    parent_row["SKU"] = parent_sku
    parent_row["Name"] = product.title or ""
    parent_row["Regular price"] = _resolve_price(product)
    parent_row["Weight (kg)"] = _resolve_weight_kg(product)
    parent_row["Images"] = _resolve_images(images)
    parent_row["In stock?"] = "1" if any(_variant_in_stock(v) for v in variants) else "0"
    _set_attributes(
        parent_row,
        option_names,
        {name: ",".join(parent_attribute_values.get(name, [])) for name in option_names},
    )
    rows.append(parent_row)

    seen_skus = {parent_sku}
    for index, variant in enumerate(variants, start=1):
        variant_row = _empty_row()
        _set_common_product_fields(variant_row, product, publish=publish)
        variant_row["Type"] = "variation"
        variant_sku_base = f"{parent_sku}:{_resolve_variant_key(variant, index)}"
        variant_sku = variant_sku_base
        suffix = 2
        while variant_sku in seen_skus:
            variant_sku = f"{variant_sku_base}-{suffix}"
            suffix += 1
        seen_skus.add(variant_sku)

        variant_row["SKU"] = variant_sku
        variant_row["Regular price"] = _resolve_price(product, variant)
        variant_row["Weight (kg)"] = _resolve_weight_kg(product, variant)
        variant_row["Images"] = str(variant.image or "")
        variant_row["Parent"] = parent_sku
        variant_row["Categories"] = ""
        variant_row["Tags"] = ""

        _apply_stock_fields(variant_row, variant)

        variant_values: dict[str, str] = {}
        for option_name in option_names:
            if option_name == "Option":
                variant_values[option_name] = _fallback_option_value(variant, index)
            else:
                variant_values[option_name] = str((variant.options or {}).get(option_name) or "")
        _set_attributes(variant_row, option_names, variant_values)
        rows.append(variant_row)

    return rows


def product_to_woocommerce_csv(product: ProductResult, *, publish: bool) -> tuple[str, str]:
    rows = product_to_woocommerce_rows(product, publish=publish)
    return utils.dict_rows_to_csv(rows, WOOCOMMERCE_COLUMNS), utils.make_export_filename("woocommerce")
