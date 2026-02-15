"""Web routes for CSV import and product-payload export: /csv, /import.csv, /export-from-product.csv."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from ..helpers.exporting import (
    batch_export_csv_for_target,
    csv_attachment_response,
    export_csv_attachment_for_product,
)
from ..helpers import importing as _importing
from ..helpers.payload import (
    decode_product_json_b64,
    product_from_payload_dict,
    product_to_json_b64,
    products_to_json_b64,
)
from ..helpers.rendering import render_web_page
from ..models import serialize_product_for_api
from ..services.exporters.weight_units import DEFAULT_WEIGHT_UNIT_BY_TARGET

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
router = APIRouter()


@router.get("/csv", response_class=HTMLResponse)
def csv_home(request: Request) -> HTMLResponse:
    return render_web_page(
        request,
        templates,
        template_name="csv.html",
        active_page="csv",
        error=None,
        product_urls=[],
        target_platform="shopify",
        weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
        bigcommerce_csv_format="modern",
        squarespace_product_page="",
        squarespace_product_url="",
        csv_source_platform="shopify",
        csv_source_weight_unit="kg",
        csv_error=None,
        preview_product_json=None,
        preview_product_json_b64=None,
    )


@router.post("/import.csv")
def import_csv_from_web(
    request: Request,
    source_platform: str = Form(...),
    source_weight_unit: str = Form(default=""),
    file: UploadFile = File(...),
) -> HTMLResponse:
    try:
        csv_bytes = file.file.read()
        products = _importing.run_import_csv_products(
            source_platform=source_platform,
            csv_bytes=csv_bytes,
            source_weight_unit=source_weight_unit,
        )
        is_batch = len(products) > 1
        editor_payloads = [serialize_product_for_api(p, include_raw=False) for p in products]

        return render_web_page(
            request,
            templates,
            template_name="csv.html",
            active_page="csv",
            error=None,
            product_urls=[],
            target_platform="shopify",
            weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
            bigcommerce_csv_format="modern",
            squarespace_product_page="",
            squarespace_product_url="",
            csv_source_platform=source_platform,
            csv_source_weight_unit=source_weight_unit or "kg",
            preview_product_json_b64=(
                products_to_json_b64(products) if is_batch
                else product_to_json_b64(products[0])
            ),
            editor_product_payload=editor_payloads[0] if not is_batch else None,
            editor_products_payload=editor_payloads if is_batch else None,
        )
    except HTTPException as exc:
        return render_web_page(
            request,
            templates,
            template_name="csv.html",
            active_page="csv",
            error=None,
            csv_error=exc.detail,
            product_urls=[],
            target_platform="shopify",
            weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
            bigcommerce_csv_format="modern",
            squarespace_product_page="",
            squarespace_product_url="",
            csv_source_platform=source_platform,
            csv_source_weight_unit=source_weight_unit or "kg",
            status_code=exc.status_code,
        )


@router.post("/export-from-product.csv")
def export_from_product_csv_web(
    product_json_b64: str = Form(...),
    target_platform: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form(default=""),
    bigcommerce_csv_format: str = Form("modern"),
    squarespace_product_page: str = Form(default=""),
    squarespace_product_url: str = Form(default=""),
) -> Response:
    payload = decode_product_json_b64(product_json_b64)
    if isinstance(payload, list):
        products = [product_from_payload_dict(p) for p in payload]
        csv_text, filename = batch_export_csv_for_target(
            products,
            target_platform=target_platform,
            publish=publish,
            weight_unit=weight_unit,
            bigcommerce_csv_format=bigcommerce_csv_format,
            squarespace_product_page=squarespace_product_page,
            squarespace_product_url=squarespace_product_url,
        )
        return csv_attachment_response(csv_text, filename)
    product = product_from_payload_dict(payload)
    return export_csv_attachment_for_product(
        product,
        target_platform=target_platform,
        publish=publish,
        weight_unit=weight_unit,
        bigcommerce_csv_format=bigcommerce_csv_format,
        squarespace_product_page=squarespace_product_page,
        squarespace_product_url=squarespace_product_url,
    )
