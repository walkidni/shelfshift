import re
from typing import Iterable

from slugify import slugify

from app.models import Product, Variant
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


def _resolve_weight_kg(product: Product, variant: Variant | None = None) -> str:
    grams = utils.resolve_weight_grams(product, variant)
    if grams is None:
        return ""
    try:
        kg = float(grams) / 1000.0
    except (TypeError, ValueError):
        return ""
    return utils.format_number(kg, decimals=6)


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
    publish: bool,
    include_descriptions: bool = True,
) -> None:
    row["Published"] = "1" if publish else "0"
    row["Is featured?"] = "0"
    row["Visibility in catalog"] = "visible"
    if include_descriptions:
        row["Short description"] = _resolve_short_description(product)
        row["Description"] = product.description or ""
    row["Tax status"] = "none" if product.is_digital else "taxable"
    row["Backorders allowed?"] = "0"
    row["Sold individually?"] = "0"
    row["Categories"] = utils.resolve_primary_category(product)
    row["Tags"] = _resolve_tags(product)


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
        row["Stock"] = str(qty)
        row["In stock?"] = "1" if qty > 0 else "0"
        return
    available = utils.resolve_variant_available(variant)
    if available is not None:
        row["In stock?"] = "1" if available else "0"
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


def _is_variable_product(product: Product, variants: list[Variant]) -> bool:
    if len(variants) > 1:
        return True
    for option in utils.resolve_option_defs(product):
        if len(utils.ordered_unique(option.values)) > 1:
            return True
    return False


def product_to_woocommerce_rows(product: Product, *, publish: bool) -> list[dict[str, str]]:
    variants = utils.resolve_variants(product)
    option_names = _resolve_option_names(product, variants)
    parent_sku = _resolve_parent_sku(product)
    images = utils.resolve_product_image_urls(product)
    option_values_by_name = {
        option.name: option.values
        for option in utils.resolve_option_defs(product)
        if option.name and option.name in option_names
    }
    variant_option_maps = [utils.resolve_variant_option_map(product, variant) for variant in variants]
    parent_attribute_values = _resolve_parent_attribute_values(
        variants,
        option_names,
        option_values_by_name,
        variant_option_maps,
    )
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
        row["Images"] = _resolve_images(images or [utils.resolve_variant_image_url(variant) or ""])
        _apply_stock_fields(row, variant)
        variant_option_values = variant_option_maps[0] if variant_option_maps else {}
        simple_values: dict[str, str] = {}
        for index, option_name in enumerate(option_names, start=1):
            if option_name == "Option":
                simple_values[option_name] = _fallback_option_value(variant, index)
            else:
                simple_values[option_name] = str(variant_option_values.get(option_name) or "")
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
        _set_common_product_fields(
            variant_row,
            product,
            publish=publish,
            include_descriptions=False,
        )
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
        variant_row["Images"] = utils.resolve_variant_image_url(variant)
        variant_row["Parent"] = parent_sku
        variant_row["Categories"] = ""
        variant_row["Tags"] = ""

        _apply_stock_fields(variant_row, variant)

        variant_option_values = variant_option_maps[index - 1]
        variant_values: dict[str, str] = {}
        for option_name in option_names:
            if option_name == "Option":
                variant_values[option_name] = _fallback_option_value(variant, index)
            else:
                variant_values[option_name] = str(variant_option_values.get(option_name) or "")
        _set_attributes(variant_row, option_names, variant_values)
        rows.append(variant_row)

    return rows


def product_to_woocommerce_csv(product: Product, *, publish: bool) -> tuple[str, str]:
    rows = product_to_woocommerce_rows(product, publish=publish)
    return utils.dict_rows_to_csv(rows, WOOCOMMERCE_COLUMNS), utils.make_export_filename("woocommerce")
