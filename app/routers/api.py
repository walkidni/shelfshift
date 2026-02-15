"""JSON API routes: /health, /api/v1/*."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from ..config import get_settings
from ..helpers.exporting import (
    batch_export_csv_for_target,
    csv_attachment_response,
    export_csv_attachment_for_product,
)
from ..helpers import importing as _importing
from ..helpers.payload import product_from_payload_dict
from ..models import serialize_product_for_api
from ..schemas import (
    ExportBigCommerceCsvRequest,
    ExportFromProductCsvRequest,
    ExportShopifyCsvRequest,
    ExportSquarespaceCsvRequest,
    ExportWixCsvRequest,
    ExportWooCommerceCsvRequest,
    ImportRequest,
)
from ..services.importer import detect_product_url

settings = get_settings()
router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@router.get("/api/v1/detect")
def detect(url: str = Query(..., description="Product URL to classify")) -> dict:
    return detect_product_url(url)


@router.post("/api/v1/import")
def import_from_api(payload: ImportRequest) -> Any:
    urls = [u.strip() for u in payload.urls_list if u.strip()]
    if not urls:
        raise HTTPException(status_code=400, detail="product_urls is required")

    if len(urls) == 1:
        product = _importing.run_import_product(urls[0])
        return serialize_product_for_api(product, include_raw=settings.debug)

    products, errors = _importing.run_import_products(urls)
    return {
        "products": [
            serialize_product_for_api(p, include_raw=settings.debug)
            for p in products
        ],
        "errors": errors,
    }


@router.post("/api/v1/import/csv")
def import_from_csv_api(
    source_platform: str = Form(...),
    source_weight_unit: str = Form(""),
    file: UploadFile = File(...),
) -> dict | list[dict]:
    csv_bytes = file.file.read()
    products = _importing.run_import_csv_products(
        source_platform=source_platform,
        csv_bytes=csv_bytes,
        source_weight_unit=source_weight_unit,
    )
    if len(products) == 1:
        return serialize_product_for_api(products[0], include_raw=settings.debug)
    return [serialize_product_for_api(p, include_raw=settings.debug) for p in products]


@router.post("/api/v1/export/from-product.csv")
def export_from_product_csv(payload: ExportFromProductCsvRequest) -> Response:
    if isinstance(payload.product, list):
        products = [product_from_payload_dict(p) for p in payload.product]
        csv_text, filename = batch_export_csv_for_target(
            products,
            target_platform=payload.target_platform,
            publish=payload.publish,
            weight_unit=payload.weight_unit,
            bigcommerce_csv_format=payload.bigcommerce_csv_format,
            squarespace_product_page=payload.squarespace_product_page,
            squarespace_product_url=payload.squarespace_product_url,
        )
        return csv_attachment_response(csv_text, filename)
    product = product_from_payload_dict(payload.product)
    return export_csv_attachment_for_product(
        product,
        target_platform=payload.target_platform,
        publish=payload.publish,
        weight_unit=payload.weight_unit,
        bigcommerce_csv_format=payload.bigcommerce_csv_format,
        squarespace_product_page=payload.squarespace_product_page,
        squarespace_product_url=payload.squarespace_product_url,
    )


@router.post("/api/v1/export/shopify.csv")
def export_shopify_csv_from_body(payload: ExportShopifyCsvRequest) -> Response:
    product = product_from_payload_dict(payload.product)
    return export_csv_attachment_for_product(
        product,
        target_platform="shopify",
        publish=payload.publish,
        weight_unit=payload.weight_unit,
    )


@router.post("/api/v1/export/bigcommerce.csv")
def export_bigcommerce_csv_from_body(payload: ExportBigCommerceCsvRequest) -> Response:
    product = product_from_payload_dict(payload.product)
    return export_csv_attachment_for_product(
        product,
        target_platform="bigcommerce",
        publish=payload.publish,
        weight_unit=payload.weight_unit,
        bigcommerce_csv_format=payload.csv_format,
    )


@router.post("/api/v1/export/wix.csv")
def export_wix_csv_from_body(payload: ExportWixCsvRequest) -> Response:
    product = product_from_payload_dict(payload.product)
    return export_csv_attachment_for_product(
        product,
        target_platform="wix",
        publish=payload.publish,
        weight_unit=payload.weight_unit,
    )


@router.post("/api/v1/export/squarespace.csv")
def export_squarespace_csv_from_body(payload: ExportSquarespaceCsvRequest) -> Response:
    product = product_from_payload_dict(payload.product)
    return export_csv_attachment_for_product(
        product,
        target_platform="squarespace",
        publish=payload.publish,
        weight_unit=payload.weight_unit,
        squarespace_product_page=payload.product_page,
        squarespace_product_url=payload.squarespace_product_url,
    )


@router.post("/api/v1/export/woocommerce.csv")
def export_woocommerce_csv_from_body(payload: ExportWooCommerceCsvRequest) -> Response:
    product = product_from_payload_dict(payload.product)
    return export_csv_attachment_for_product(
        product,
        target_platform="woocommerce",
        publish=payload.publish,
        weight_unit=payload.weight_unit,
    )
