"""CSV export helpers."""


from fastapi import HTTPException
from fastapi.responses import Response

from ...core.canonical.entities import Product
from ...core.exporters import (
    product_to_bigcommerce_csv,
    product_to_shopify_csv,
    product_to_squarespace_csv,
    product_to_wix_csv,
    product_to_woocommerce_csv,
    products_to_bigcommerce_csv,
    products_to_shopify_csv,
    products_to_squarespace_csv,
    products_to_wix_csv,
    products_to_woocommerce_csv,
    resolve_weight_unit,
)
from . import importing as _importing


def _resolve_weight_unit_or_422(target_platform: str, weight_unit: str) -> str:
    try:
        return resolve_weight_unit(target_platform, weight_unit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def export_csv_for_target(
    product: Product,
    *,
    target_platform: str,
    publish: bool,
    weight_unit: str,
    bigcommerce_csv_format: str,
    squarespace_product_page: str,
    squarespace_product_url: str,
) -> tuple[str, str]:
    target = (target_platform or "").strip().lower()
    resolved_weight_unit = _resolve_weight_unit_or_422(target, weight_unit)

    if target == "shopify":
        return product_to_shopify_csv(product, publish=publish, weight_unit=resolved_weight_unit)
    if target == "bigcommerce":
        return product_to_bigcommerce_csv(
            product,
            publish=publish,
            csv_format=bigcommerce_csv_format,
            weight_unit=resolved_weight_unit,
        )
    if target == "wix":
        return product_to_wix_csv(product, publish=publish, weight_unit=resolved_weight_unit)
    if target == "squarespace":
        return product_to_squarespace_csv(
            product,
            publish=publish,
            product_page=squarespace_product_page,
            product_url=squarespace_product_url,
            weight_unit=resolved_weight_unit,
        )
    if target == "woocommerce":
        return product_to_woocommerce_csv(product, publish=publish, weight_unit=resolved_weight_unit)

    raise HTTPException(
        status_code=422,
        detail="target_platform must be one of: shopify, bigcommerce, wix, squarespace, woocommerce",
    )


def batch_export_csv_for_target(
    products: list[Product],
    *,
    target_platform: str,
    publish: bool,
    weight_unit: str,
    bigcommerce_csv_format: str,
    squarespace_product_page: str,
    squarespace_product_url: str,
) -> tuple[str, str]:
    target = (target_platform or "").strip().lower()
    resolved_weight_unit = _resolve_weight_unit_or_422(target, weight_unit)

    try:
        if target == "shopify":
            return products_to_shopify_csv(products, publish=publish, weight_unit=resolved_weight_unit)
        if target == "bigcommerce":
            return products_to_bigcommerce_csv(
                products,
                publish=publish,
                csv_format=bigcommerce_csv_format,
                weight_unit=resolved_weight_unit,
            )
        if target == "wix":
            return products_to_wix_csv(products, publish=publish, weight_unit=resolved_weight_unit)
        if target == "squarespace":
            return products_to_squarespace_csv(
                products,
                publish=publish,
                product_page=squarespace_product_page,
                product_url=squarespace_product_url,
                weight_unit=resolved_weight_unit,
            )
        if target == "woocommerce":
            return products_to_woocommerce_csv(products, publish=publish, weight_unit=resolved_weight_unit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    raise HTTPException(
        status_code=422,
        detail="target_platform must be one of: shopify, bigcommerce, wix, squarespace, woocommerce",
    )


def csv_attachment_response(csv_text: str, filename: str) -> Response:
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def export_csv_attachment_for_target(
    product_url: str,
    *,
    target_platform: str,
    publish: bool,
    weight_unit: str,
    bigcommerce_csv_format: str = "modern",
    squarespace_product_page: str = "",
    squarespace_product_url: str = "",
) -> Response:
    product = _importing.run_import_product(product_url)
    csv_text, filename = export_csv_for_target(
        product,
        target_platform=target_platform,
        publish=publish,
        weight_unit=weight_unit,
        bigcommerce_csv_format=bigcommerce_csv_format,
        squarespace_product_page=squarespace_product_page,
        squarespace_product_url=squarespace_product_url,
    )
    return csv_attachment_response(csv_text, filename)


def export_csv_attachment_for_product(
    product: Product,
    *,
    target_platform: str,
    publish: bool,
    weight_unit: str,
    bigcommerce_csv_format: str = "modern",
    squarespace_product_page: str = "",
    squarespace_product_url: str = "",
) -> Response:
    csv_text, filename = export_csv_for_target(
        product,
        target_platform=target_platform,
        publish=publish,
        weight_unit=weight_unit,
        bigcommerce_csv_format=bigcommerce_csv_format,
        squarespace_product_page=squarespace_product_page,
        squarespace_product_url=squarespace_product_url,
    )
    return csv_attachment_response(csv_text, filename)
