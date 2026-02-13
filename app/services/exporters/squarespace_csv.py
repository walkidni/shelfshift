from app.models import Product, Variant
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


def _resolve_option_names(product: Product, variants: list[Variant]) -> list[str]:
    option_names = [option.name for option in utils.resolve_option_defs(product) if option.name]
    if not option_names and len(variants) > 1:
        return ["Option"]
    return option_names[:3]


def _resolve_price(product: Product, variant: Variant) -> str:
    amount = utils.resolve_price_amount(product, variant)
    return utils.format_number(amount, decimals=2) if amount is not None else ""


def _resolve_stock(product: Product, variant: Variant) -> str:
    if not utils.resolve_variant_track_quantity(product, variant):
        return "Unlimited"
    qty = utils.resolve_variant_inventory_quantity(variant)
    if qty is None:
        return "Unlimited"
    return str(qty)


def _resolve_weight_kg(product: Product, variant: Variant) -> str:
    grams = variant.weight if variant.weight is not None else product.weight
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


def _resolve_hosted_image_urls(product: Product) -> str:
    return "\n".join(utils.resolve_product_image_urls(product))


def _fallback_option_value(variant: Variant, index: int) -> str:
    return str(variant.title or variant.sku or variant.id or f"Variant {index}")


def _set_variant_option_fields(
    row: dict[str, str],
    option_names: list[str],
    variant: Variant,
    *,
    index: int,
    values_by_name: dict[str, str],
) -> None:
    for option_index, option_name in enumerate(option_names, start=1):
        row[f"Option Name {option_index}"] = option_name
        if option_name == "Option":
            row[f"Option Value {option_index}"] = _fallback_option_value(variant, index)
            continue
        row[f"Option Value {option_index}"] = str(values_by_name.get(option_name) or "")


def product_to_squarespace_rows(
    product: Product,
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
        variant_option_values = utils.resolve_variant_option_map(product, variant)
        row["SKU"] = str(variant.sku or variant.id or "")
        row["Price"] = _resolve_price(product, variant)
        row["Sale Price"] = ""
        row["On Sale"] = "No"
        row["Stock"] = _resolve_stock(product, variant)
        _set_variant_option_fields(
            row,
            option_names,
            variant,
            index=index,
            values_by_name=variant_option_values,
        )

        if index == 1:
            row["Product Type [Non Editable]"] = "DIGITAL" if product.is_digital else "PHYSICAL"
            row["Product Page"] = (product_page or "").strip()
            row["Product URL"] = (product_url or "").strip()
            row["Title"] = product.title or ""
            row["Description"] = product.description or ""
            row["Categories"] = utils.resolve_primary_category(product)
            row["Tags"] = _resolve_tags(product)
            row["Weight"] = _resolve_weight_kg(product, variant)
            row["Visible"] = _format_bool(publish)
            row["Hosted Image URLs"] = hosted_image_urls

        rows.append(row)

    return rows


def product_to_squarespace_csv(
    product: Product,
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
