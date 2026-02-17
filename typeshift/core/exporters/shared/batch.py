
from ...canonical import Product

from . import utils
from ..platforms.bigcommerce import (
    BIGCOMMERCE_COLUMNS,
    BIGCOMMERCE_LEGACY_COLUMNS,
    BigCommerceCsvFormat,
    product_to_bigcommerce_rows,
)
from ..platforms.shopify import SHOPIFY_COLUMNS, product_to_shopify_rows
from ..platforms.squarespace import SQUARESPACE_COLUMNS, product_to_squarespace_rows
from ..platforms.wix import WIX_COLUMNS, product_to_wix_rows
from ..platforms.woocommerce import WOOCOMMERCE_COLUMNS, product_to_woocommerce_rows


def _require_non_empty_products(products: list[Product], *, label: str) -> None:
    if not products:
        raise ValueError(f"{label} requires at least one product.")


def _require_unique(values: list[str], *, label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if not value:
            continue
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"Duplicate {label} values in batch export: {joined}")


def products_to_shopify_csv(
    products: list[Product],
    *,
    publish: bool,
    weight_unit: str = "g",
) -> tuple[str, str]:
    _require_non_empty_products(products, label="Shopify batch export")
    rows: list[dict[str, str]] = []
    handles: list[str] = []
    for product in products:
        product_rows = product_to_shopify_rows(product, publish=publish, weight_unit=weight_unit)
        if product_rows:
            handles.append(str(product_rows[0].get("Handle") or "").strip())
        rows.extend(product_rows)

    _require_unique(handles, label="Shopify Handle")
    return utils.dict_rows_to_csv(rows, SHOPIFY_COLUMNS), utils.make_export_filename("shopify")


def products_to_bigcommerce_csv(
    products: list[Product],
    *,
    publish: bool,
    csv_format: BigCommerceCsvFormat = "modern",
    weight_unit: str = "kg",
) -> tuple[str, str]:
    _require_non_empty_products(products, label="BigCommerce batch export")
    rows: list[dict[str, str]] = []
    product_keys: list[str] = []
    for product in products:
        product_rows = product_to_bigcommerce_rows(
            product,
            publish=publish,
            csv_format=csv_format,
            weight_unit=weight_unit,
        )
        if csv_format == "modern":
            product_row = next((row for row in product_rows if row.get("Item") == "Product"), None)
            if product_row is not None:
                product_keys.append(str(product_row.get("SKU") or "").strip())
        else:
            if product_rows:
                product_keys.append(str(product_rows[0].get("Code") or "").strip())
        rows.extend(product_rows)

    _require_unique(
        product_keys,
        label="BigCommerce SKU" if csv_format == "modern" else "BigCommerce Code",
    )
    columns = BIGCOMMERCE_COLUMNS if csv_format == "modern" else BIGCOMMERCE_LEGACY_COLUMNS
    return utils.dict_rows_to_csv(rows, columns), utils.make_export_filename("bigcommerce")


def products_to_wix_csv(
    products: list[Product],
    *,
    publish: bool,
    weight_unit: str = "kg",
) -> tuple[str, str]:
    _require_non_empty_products(products, label="Wix batch export")
    rows: list[dict[str, str]] = []
    handles: list[str] = []
    for product in products:
        product_rows = product_to_wix_rows(product, publish=publish, weight_unit=weight_unit)
        product_row = next((row for row in product_rows if row.get("fieldType") == "PRODUCT"), None)
        if product_row is not None:
            handles.append(str(product_row.get("handle") or "").strip())
        rows.extend(product_rows)

    _require_unique(handles, label="Wix handle")
    return utils.dict_rows_to_csv(rows, WIX_COLUMNS), utils.make_export_filename("wix")


def products_to_squarespace_csv(
    products: list[Product],
    *,
    publish: bool,
    product_page: str = "",
    product_url: str = "",
    weight_unit: str = "kg",
) -> tuple[str, str]:
    _require_non_empty_products(products, label="Squarespace batch export")
    rows: list[dict[str, str]] = []
    for product in products:
        rows.extend(
            product_to_squarespace_rows(
                product,
                publish=publish,
                product_page=product_page,
                product_url=product_url,
                weight_unit=weight_unit,
            )
        )
    # Squarespace's `product_page`/`product_url` are intentionally left blank in batch flows for now.
    return utils.dict_rows_to_csv(rows, SQUARESPACE_COLUMNS), utils.make_export_filename("squarespace")


def products_to_woocommerce_csv(
    products: list[Product],
    *,
    publish: bool,
    weight_unit: str = "kg",
) -> tuple[str, str]:
    _require_non_empty_products(products, label="WooCommerce batch export")
    rows: list[dict[str, str]] = []
    parent_skus: list[str] = []
    for product in products:
        product_rows = product_to_woocommerce_rows(product, publish=publish, weight_unit=weight_unit)
        parent_row = next(
            (row for row in product_rows if row.get("Parent") in {"", None} and row.get("SKU")),
            None,
        )
        if parent_row is not None:
            parent_skus.append(str(parent_row.get("SKU") or "").strip())
        rows.extend(product_rows)

    _require_unique(parent_skus, label="WooCommerce parent SKU")
    return utils.dict_rows_to_csv(rows, WOOCOMMERCE_COLUMNS), utils.make_export_filename("woocommerce")


__all__ = [
    "products_to_bigcommerce_csv",
    "products_to_shopify_csv",
    "products_to_squarespace_csv",
    "products_to_wix_csv",
    "products_to_woocommerce_csv",
]

