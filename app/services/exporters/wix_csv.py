import re

from slugify import slugify

from ..importer import ProductResult, Variant
from . import utils

_WIX_HEADER = (
    "handle,fieldType,name,visible,plainDescription,media,mediaAltText,ribbon,brand,price,strikethroughPrice,"
    "baseUnit,baseUnitMeasurement,totalUnits,totalUnitsMeasurement,cost,inventory,preOrderEnabled,preOrderMessage,"
    "preOrderLimit,sku,barcode,weight,productOptionName1,productOptionType1,productOptionChoices1,productOptionName2,"
    "productOptionType2,productOptionChoices2,productOptionName3,productOptionType3,productOptionChoices3,"
    "productOptionName4,productOptionType4,productOptionChoices4,productOptionName5,productOptionType5,"
    "productOptionChoices5,productOptionName6,productOptionType6,productOptionChoices6,modifierName1,modifierType1,"
    "modifierCharLimit1,modifierMandatory1,modifierDescription1,modifierName2,modifierType2,modifierCharLimit2,"
    "modifierMandatory2,modifierDescription2,modifierName3,modifierType3,modifierCharLimit3,modifierMandatory3,"
    "modifierDescription3,modifierName4,modifierType4,modifierCharLimit4,modifierMandatory4,modifierDescription4,"
    "modifierName5,modifierType5,modifierCharLimit5,modifierMandatory5,modifierDescription5,modifierName6,"
    "modifierType6,modifierCharLimit6,modifierMandatory6,modifierDescription6,modifierName7,modifierType7,"
    "modifierCharLimit7,modifierMandatory7,modifierDescription7,modifierName8,modifierType8,modifierCharLimit8,"
    "modifierMandatory8,modifierDescription8,modifierName9,modifierType9,modifierCharLimit9,modifierMandatory9,"
    "modifierDescription9,modifierName10,modifierType10,modifierCharLimit10,modifierMandatory10,modifierDescription10"
)

WIX_COLUMNS: list[str] = _WIX_HEADER.split(",")

_HANDLE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_OPTIONS = 6
_DEFAULT_OPTION_TYPE = "TEXT_CHOICES"
_MAX_WIX_NAME_LEN = 80
_MAX_WIX_PLAIN_DESCRIPTION_LEN = 16000


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


def _truncate(value: str | None, max_len: int) -> str:
    text = str(value or "")
    if not text:
        return ""

    units = 0
    out: list[str] = []
    for ch in text:
        # Wix validation appears to use UTF-16 code units (JS-style length).
        ch_units = 2 if ord(ch) > 0xFFFF else 1
        if units + ch_units > max_len:
            break
        out.append(ch)
        units += ch_units
    return "".join(out)


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


def _resolve_weight_kg(product: ProductResult, variant: Variant | None = None) -> str:
    grams = variant.weight if variant and variant.weight is not None else product.weight
    if grams is None:
        return ""
    try:
        kg = float(grams) / 1000.0
    except (TypeError, ValueError):
        return ""
    return utils.format_number(kg, decimals=6)


def _resolve_option_names(product: ProductResult, variants: list[Variant]) -> list[str]:
    option_names = utils.ordered_unique((product.options or {}).keys())
    if len(option_names) < _MAX_OPTIONS:
        for variant in variants:
            for option_name in utils.ordered_unique((variant.options or {}).keys()):
                if option_name in option_names:
                    continue
                option_names.append(option_name)
                if len(option_names) == _MAX_OPTIONS:
                    break
            if len(option_names) == _MAX_OPTIONS:
                break

    if not option_names and len(variants) > 1:
        return ["Option"]
    return option_names[:_MAX_OPTIONS]


def _fallback_option_value(variant: Variant, index: int) -> str:
    return str(variant.title or variant.sku or variant.id or f"Variant {index}")


def _resolve_product_option_choices(
    product: ProductResult,
    variants: list[Variant],
    option_name: str,
) -> str:
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
            continue
        value = str((variant.options or {}).get(option_name) or "")
        if value:
            values.append(value)

    return ";".join(utils.ordered_unique(values))


def _resolve_variant_option_choice(option_name: str, variant: Variant, *, index: int) -> str:
    if option_name == "Option":
        return _fallback_option_value(variant, index)
    return str((variant.options or {}).get(option_name) or "")


def _set_option_fields(
    row: dict[str, str],
    option_names: list[str],
    product: ProductResult,
    variants: list[Variant],
    *,
    variant: Variant | None,
    index: int,
) -> None:
    for option_index, option_name in enumerate(option_names, start=1):
        row[f"productOptionName{option_index}"] = option_name
        row[f"productOptionType{option_index}"] = _DEFAULT_OPTION_TYPE
        if variant is None:
            row[f"productOptionChoices{option_index}"] = _resolve_product_option_choices(product, variants, option_name)
        else:
            row[f"productOptionChoices{option_index}"] = _resolve_variant_option_choice(option_name, variant, index=index)


def _variant_in_stock(product: ProductResult, variant: Variant) -> bool:
    if variant.inventory_quantity is not None:
        try:
            return int(variant.inventory_quantity) > 0
        except (TypeError, ValueError):
            return False
    if variant.available is not None:
        return bool(variant.available)
    return not product.track_quantity


def _resolve_variant_inventory(product: ProductResult, variant: Variant) -> str:
    qty = _format_inventory_qty(variant.inventory_quantity)
    if qty:
        return qty
    if variant.available is not None:
        return "IN_STOCK" if variant.available else "OUT_OF_STOCK"
    if not product.track_quantity:
        return "IN_STOCK"
    return ""


def _resolve_product_inventory(product: ProductResult, variants: list[Variant]) -> str:
    quantities: list[int] = []
    for variant in variants:
        if variant.inventory_quantity is None:
            continue
        try:
            quantities.append(max(0, int(variant.inventory_quantity)))
        except (TypeError, ValueError):
            continue

    if quantities:
        return str(sum(quantities))

    in_stock = any(_variant_in_stock(product, variant) for variant in variants)
    if in_stock:
        return "IN_STOCK"
    if not product.track_quantity:
        return "IN_STOCK"
    return "OUT_OF_STOCK"


def product_to_wix_rows(product: ProductResult, *, publish: bool) -> list[dict[str, str]]:
    handle = _resolve_handle(product)
    variants = utils.resolve_variants(product)
    images = utils.ordered_unique(product.images or [])
    option_names = _resolve_option_names(product, variants)

    rows: list[dict[str, str]] = []

    first_variant = variants[0] if variants else None
    product_row = _empty_row()
    product_row["handle"] = handle
    product_row["fieldType"] = "PRODUCT"
    product_row["name"] = _truncate(product.title, _MAX_WIX_NAME_LEN)
    product_row["visible"] = _format_bool(publish)
    product_row["plainDescription"] = _truncate(product.description, _MAX_WIX_PLAIN_DESCRIPTION_LEN)
    product_row["brand"] = product.vendor or product.brand or ""
    product_row["price"] = _resolve_price(product, first_variant)
    product_row["inventory"] = _resolve_product_inventory(product, variants)
    product_row["sku"] = str((first_variant.sku if first_variant else None) or product.id or "")
    product_row["weight"] = _resolve_weight_kg(product, first_variant)
    if images:
        product_row["media"] = images[0]
        product_row["mediaAltText"] = (product.title or "").strip()

    _set_option_fields(product_row, option_names, product, variants, variant=None, index=0)
    rows.append(product_row)

    for index, variant in enumerate(variants, start=1):
        variant_row = _empty_row()
        variant_row["handle"] = handle
        variant_row["fieldType"] = "VARIANT"
        variant_row["visible"] = _format_bool(publish)
        variant_row["price"] = _resolve_price(product, variant)
        variant_row["inventory"] = _resolve_variant_inventory(product, variant)
        variant_row["sku"] = str(variant.sku or variant.id or "")
        variant_row["weight"] = _resolve_weight_kg(product, variant)

        _set_option_fields(variant_row, option_names, product, variants, variant=variant, index=index)
        rows.append(variant_row)

    for image_url in images[1:]:
        media_row = _empty_row()
        media_row["handle"] = handle
        media_row["fieldType"] = "MEDIA"
        media_row["media"] = image_url
        media_row["mediaAltText"] = (product.title or "").strip()
        rows.append(media_row)

    return rows


def product_to_wix_csv(product: ProductResult, *, publish: bool) -> tuple[str, str]:
    rows = product_to_wix_rows(product, publish=publish)
    return utils.dict_rows_to_csv(rows, WIX_COLUMNS), utils.make_export_filename("wix")
