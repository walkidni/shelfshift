from ...canonical import Product, Variant
from ..shared import utils
from ..shared.weight_units import resolve_weight_unit

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
    "Option Name 4",
    "Option Value 4",
    "Option Name 5",
    "Option Value 5",
    "Option Name 6",
    "Option Value 6",
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


class _SquarespaceExportHeaders:
    product_type = "Product Type [Non Editable]"
    product_page = "Product Page"
    product_url = "Product URL"
    title = "Title"
    description = "Description"
    sku = "SKU"
    price = "Price"
    sale_price = "Sale Price"
    on_sale = "On Sale"
    stock = "Stock"
    categories = "Categories"
    tags = "Tags"
    weight = "Weight"
    visible = "Visible"
    hosted_image_urls = "Hosted Image URLs"


H = _SquarespaceExportHeaders()
_SQUARESPACE_CANONICAL_HEADERS: set[str] = utils.infer_export_canonical_headers(
    export_headers=H,
    indexed_header_families=[(("Option Name {i}", "Option Value {i}"), range(1, 7))],
)


def _set_cell(row: dict[str, str], header: str, value: str) -> None:
    if header not in row:
        raise ValueError(f"Unknown Squarespace header assignment: {header}")
    row[header] = value


def _empty_row() -> dict[str, str]:
    return dict.fromkeys(SQUARESPACE_COLUMNS, "")


def _format_bool(value: bool) -> str:
    return "Yes" if value else "No"


def _resolve_option_names(product: Product, variants: list[Variant]) -> list[str]:
    option_names = [option.name for option in utils.resolve_option_defs(product) if option.name]
    if not option_names and len(variants) > 1:
        return ["Option"]
    return option_names[:6]


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


def _resolve_weight(product: Product, variant: Variant, *, weight_unit: str) -> str:
    grams = utils.resolve_weight_grams(product, variant)
    converted = utils.convert_weight_from_grams(grams, unit=weight_unit)
    if converted is None:
        return ""
    return utils.format_number(converted, decimals=6)


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
        _set_cell(row, f"Option Name {option_index}", option_name)
        if option_name == "Option":
            _set_cell(row, f"Option Value {option_index}", _fallback_option_value(variant, index))
            continue
        _set_cell(row, f"Option Value {option_index}", str(values_by_name.get(option_name) or ""))


def product_to_squarespace_rows(
    product: Product,
    *,
    publish: bool | None = None,
    product_page: str = "",
    product_url: str = "",
    weight_unit: str = "kg",
) -> list[dict[str, str]]:
    resolved_weight_unit = resolve_weight_unit("squarespace", weight_unit)
    is_visible = utils.resolve_product_visibility(product, publish_override=publish)
    variants = utils.resolve_variants(product)
    option_names = _resolve_option_names(product, variants)
    hosted_image_urls = _resolve_hosted_image_urls(product)

    rows: list[dict[str, str]] = []
    for index, variant in enumerate(variants, start=1):
        row = _empty_row()
        variant_option_values = utils.resolve_variant_option_map(product, variant)
        _set_cell(row, H.sku, str(variant.sku or variant.id or ""))
        _set_cell(row, H.price, _resolve_price(product, variant))
        _set_cell(row, H.sale_price, "")
        _set_cell(row, H.on_sale, "No")
        _set_cell(row, H.stock, _resolve_stock(product, variant))
        _set_variant_option_fields(
            row,
            option_names,
            variant,
            index=index,
            values_by_name=variant_option_values,
        )

        if index == 1:
            _set_cell(row, H.product_type, "DIGITAL" if product.is_digital else "PHYSICAL")
            _set_cell(row, H.product_page, (product_page or "").strip())
            _set_cell(row, H.product_url, (product_url or "").strip())
            _set_cell(row, H.title, product.title or "")
            _set_cell(row, H.description, product.description or "")
            # Squarespace imports often fail with "Categories not assigned" when
            # the category label doesn't already exist in the destination site.
            # Keep Categories blank so users can assign categories post-import.
            _set_cell(row, H.categories, "")
            _set_cell(row, H.tags, _resolve_tags(product))
            _set_cell(
                row, H.weight, _resolve_weight(product, variant, weight_unit=resolved_weight_unit)
            )
            _set_cell(row, H.visible, _format_bool(is_visible))
            _set_cell(row, H.hosted_image_urls, hosted_image_urls)
            utils.apply_platform_unmapped_fields_to_row(
                row,
                product,
                platform="squarespace",
                canonical_headers=_SQUARESPACE_CANONICAL_HEADERS,
            )

        utils.apply_platform_unmapped_fields_to_row(
            row,
            product,
            platform="squarespace",
            canonical_headers=_SQUARESPACE_CANONICAL_HEADERS,
            variant=variant,
        )

        rows.append(row)

    return rows


def product_to_squarespace_csv(
    product: Product,
    *,
    publish: bool | None = None,
    product_page: str = "",
    product_url: str = "",
    weight_unit: str = "kg",
) -> tuple[str, str]:
    rows = product_to_squarespace_rows(
        product,
        publish=publish,
        product_page=product_page,
        product_url=product_url,
        weight_unit=weight_unit,
    )
    return utils.dict_rows_to_csv(rows, SQUARESPACE_COLUMNS), utils.make_export_filename(
        "squarespace"
    )
