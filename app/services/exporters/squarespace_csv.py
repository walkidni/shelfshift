from app.models import ProductResult, Variant
from . import utils

SQUARESPACE_COLUMNS: list[str] = [
    "Product ID [Non Editable]",
    "Variant ID [Non Editable]",
    "Product Type [Non Editable]",
    "Product Page",
    "Product URL",
    "Title",
    "Description",
    "SKU",
    "Option Name 1",
    "Option Value 1",
    "Option Name 2",
    "Option Value 2",
    "Option Name 3",
    "Option Value 3",
    "Price",
    "Sale Price",
    "On Sale",
    "Stock",
    "Categories",
    "Tags",
    "Weight",
    "Length",
    "Width",
    "Height",
    "Visible",
    "Hosted Image URLs",
]


def _empty_row() -> dict[str, str]:
    return {column: "" for column in SQUARESPACE_COLUMNS}


def _format_bool(value: bool) -> str:
    return "Yes" if value else "No"


def _resolve_option_names(product: ProductResult, variants: list[Variant]) -> list[str]:
    option_names = utils.ordered_unique((product.options or {}).keys())
    if len(option_names) < 3:
        for variant in variants:
            for option_name in utils.ordered_unique((variant.options or {}).keys()):
                if option_name in option_names:
                    continue
                option_names.append(option_name)
                if len(option_names) == 3:
                    break
            if len(option_names) == 3:
                break
    if not option_names and len(variants) > 1:
        return ["Option"]
    return option_names[:3]


def _resolve_price(product: ProductResult, variant: Variant) -> str:
    if variant.price_amount is not None:
        return utils.format_number(variant.price_amount, decimals=2)
    if isinstance(product.price, dict):
        amount = product.price.get("amount")
        if isinstance(amount, (int, float)):
            return utils.format_number(float(amount), decimals=2)
    return ""


def _resolve_stock(product: ProductResult, variant: Variant) -> str:
    if not product.track_quantity:
        return "Unlimited"
    if variant.inventory_quantity is None:
        return "Unlimited"
    try:
        return str(max(0, int(variant.inventory_quantity)))
    except (TypeError, ValueError):
        return "Unlimited"


def _resolve_weight_kg(product: ProductResult, variant: Variant) -> str:
    grams = variant.weight if variant.weight is not None else product.weight
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


def _resolve_hosted_image_urls(product: ProductResult) -> str:
    return "\n".join(utils.ordered_unique(product.images or []))


def _fallback_option_value(variant: Variant, index: int) -> str:
    return str(variant.title or variant.sku or variant.id or f"Variant {index}")


def _set_variant_option_fields(
    row: dict[str, str],
    option_names: list[str],
    variant: Variant,
    *,
    index: int,
) -> None:
    for option_index, option_name in enumerate(option_names, start=1):
        row[f"Option Name {option_index}"] = option_name
        if option_name == "Option":
            row[f"Option Value {option_index}"] = _fallback_option_value(variant, index)
            continue
        row[f"Option Value {option_index}"] = str((variant.options or {}).get(option_name) or "")


def product_to_squarespace_rows(
    product: ProductResult,
    *,
    publish: bool,
    product_page: str = "",
    product_url: str = "",
) -> list[dict[str, str]]:
    variants = utils.resolve_variants(product)
    option_names = _resolve_option_names(product, variants)
    hosted_image_urls = _resolve_hosted_image_urls(product)

    rows: list[dict[str, str]] = []
    for index, variant in enumerate(variants, start=1):
        row = _empty_row()
        row["SKU"] = str(variant.sku or variant.id or "")
        row["Price"] = _resolve_price(product, variant)
        row["Sale Price"] = ""
        row["On Sale"] = "No"
        row["Stock"] = _resolve_stock(product, variant)
        _set_variant_option_fields(row, option_names, variant, index=index)

        if index == 1:
            row["Product Type [Non Editable]"] = "DIGITAL" if product.is_digital else "PHYSICAL"
            row["Product Page"] = (product_page or "").strip()
            row["Product URL"] = (product_url or "").strip()
            row["Title"] = product.title or ""
            row["Description"] = product.description or ""
            row["Categories"] = (product.category or "").strip()
            row["Tags"] = _resolve_tags(product)
            row["Weight"] = _resolve_weight_kg(product, variant)
            row["Visible"] = _format_bool(publish)
            row["Hosted Image URLs"] = hosted_image_urls

        rows.append(row)

    return rows


def product_to_squarespace_csv(
    product: ProductResult,
    *,
    publish: bool,
    product_page: str = "",
    product_url: str = "",
) -> tuple[str, str]:
    rows = product_to_squarespace_rows(
        product,
        publish=publish,
        product_page=product_page,
        product_url=product_url,
    )
    return utils.dict_rows_to_csv(rows, SQUARESPACE_COLUMNS), utils.make_export_filename("squarespace")
