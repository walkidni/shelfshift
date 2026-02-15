"""Web routes for URL-based import and direct export: /, /import.url, /export.csv, /export/*.csv."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from ..helpers import importing as _importing
from ..helpers.exporting import export_csv_attachment_for_target
from ..helpers.payload import product_to_json_b64, products_to_json_b64
from ..helpers.rendering import render_web_page
from ..models import serialize_product_for_api
from ..services.exporters.weight_units import DEFAULT_WEIGHT_UNIT_BY_TARGET

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return render_web_page(
        request,
        templates,
        template_name="index.html",
        active_page="url",
        error=None,
        product_urls=[],
        target_platform="shopify",
        weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
        bigcommerce_csv_format="modern",
        squarespace_product_page="",
        squarespace_product_url="",
    )


@router.post("/import.url")
def import_url_from_web(
    request: Request,
    product_urls: list[str] = Form(...),
) -> HTMLResponse:
    urls = [u.strip() for u in product_urls if u.strip()]
    if not urls:
        return render_web_page(
            request,
            templates,
            template_name="index.html",
            active_page="url",
            error="At least one product URL is required.",
            error_title="Import Error",
            product_urls=[],
            target_platform="shopify",
            weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
            bigcommerce_csv_format="modern",
            squarespace_product_page="",
            squarespace_product_url="",
            status_code=400,
        )

    if len(urls) == 1:
        try:
            product = _importing.run_import_product(urls[0])
            editor_payload = serialize_product_for_api(product, include_raw=False)
            return render_web_page(
                request,
                templates,
                template_name="index.html",
                active_page="url",
                error=None,
                error_title="Import Error",
                product_urls=urls,
                target_platform="shopify",
                weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
                bigcommerce_csv_format="modern",
                squarespace_product_page="",
                squarespace_product_url="",
                preview_product_json_b64=product_to_json_b64(product),
                editor_product_payload=editor_payload,
            )
        except HTTPException as exc:
            return render_web_page(
                request,
                templates,
                template_name="index.html",
                active_page="url",
                error=exc.detail,
                error_title="Import Error",
                product_urls=urls,
                target_platform="shopify",
                weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
                bigcommerce_csv_format="modern",
                squarespace_product_page="",
                squarespace_product_url="",
                status_code=exc.status_code,
            )

    # -- batch import (multiple URLs, partial-success) --
    products, import_errors = _importing.run_import_products(urls)
    if not products:
        return render_web_page(
            request,
            templates,
            template_name="index.html",
            active_page="url",
            error="All URL imports failed.",
            error_title="Import Error",
            product_urls=urls,
            target_platform="shopify",
            weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
            bigcommerce_csv_format="modern",
            squarespace_product_page="",
            squarespace_product_url="",
            url_import_errors=import_errors,
            status_code=422,
        )

    editor_payloads = [serialize_product_for_api(p, include_raw=False) for p in products]
    is_batch = len(products) > 1
    return render_web_page(
        request,
        templates,
        template_name="index.html",
        active_page="url",
        error=None,
        error_title="Import Error",
        product_urls=urls,
        target_platform="shopify",
        weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
        bigcommerce_csv_format="modern",
        squarespace_product_page="",
        squarespace_product_url="",
        preview_product_json_b64=(
            products_to_json_b64(products) if is_batch
            else product_to_json_b64(products[0])
        ),
        editor_product_payload=editor_payloads[0] if not is_batch else None,
        editor_products_payload=editor_payloads if is_batch else None,
        url_import_errors=import_errors if import_errors else None,
    )


@router.post("/export/shopify.csv")
def export_shopify_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form("g"),
) -> Response:
    return export_csv_attachment_for_target(
        product_url,
        target_platform="shopify",
        publish=publish,
        weight_unit=weight_unit,
    )


@router.post("/export/bigcommerce.csv")
def export_bigcommerce_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    csv_format: str = Form("modern"),
    weight_unit: str = Form("kg"),
) -> Response:
    return export_csv_attachment_for_target(
        product_url,
        target_platform="bigcommerce",
        publish=publish,
        weight_unit=weight_unit,
        bigcommerce_csv_format=csv_format,
    )


@router.post("/export/wix.csv")
def export_wix_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form("kg"),
) -> Response:
    return export_csv_attachment_for_target(
        product_url,
        target_platform="wix",
        publish=publish,
        weight_unit=weight_unit,
    )


@router.post("/export/squarespace.csv")
def export_squarespace_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    squarespace_product_page: str = Form(default=""),
    squarespace_product_url: str = Form(default=""),
    weight_unit: str = Form("kg"),
) -> Response:
    return export_csv_attachment_for_target(
        product_url,
        target_platform="squarespace",
        publish=publish,
        weight_unit=weight_unit,
        squarespace_product_page=squarespace_product_page,
        squarespace_product_url=squarespace_product_url,
    )


@router.post("/export/woocommerce.csv")
def export_woocommerce_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form("kg"),
) -> Response:
    return export_csv_attachment_for_target(
        product_url,
        target_platform="woocommerce",
        publish=publish,
        weight_unit=weight_unit,
    )


@router.post("/export.csv")
def export_csv_from_web(
    request: Request,
    product_url: str = Form(...),
    target_platform: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form(default=""),
    bigcommerce_csv_format: str = Form("modern"),
    squarespace_product_page: str = Form(default=""),
    squarespace_product_url: str = Form(default=""),
) -> Response:
    try:
        return export_csv_attachment_for_target(
            product_url,
            target_platform=target_platform,
            publish=publish,
            weight_unit=weight_unit,
            bigcommerce_csv_format=bigcommerce_csv_format,
            squarespace_product_page=squarespace_product_page,
            squarespace_product_url=squarespace_product_url,
        )
    except HTTPException as exc:
        return render_web_page(
            request,
            templates,
            template_name="index.html",
            active_page="url",
            error=exc.detail,
            error_title="Export Error",
            product_urls=[product_url],
            target_platform=target_platform,
            weight_unit=weight_unit,
            bigcommerce_csv_format=bigcommerce_csv_format,
            squarespace_product_page=squarespace_product_page,
            squarespace_product_url=squarespace_product_url,
            status_code=exc.status_code,
        )
