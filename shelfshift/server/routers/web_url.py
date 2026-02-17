"""Web routes for URL-based import and direct export."""


from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from ...core.api import export_csv
from ...core.canonical.serialization import serialize_product_for_api
from ...core.exporters.shared.weight_units import DEFAULT_WEIGHT_UNIT_BY_TARGET
from ..helpers import importing as _importing_helpers
from ..helpers.payload import product_to_json_b64, products_to_json_b64
from ..helpers.rendering import render_landing_page, render_web_page

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
	return render_landing_page(request, templates)


@router.get("/url", response_class=HTMLResponse)
def url_import_page(request: Request) -> HTMLResponse:
	return render_web_page(
		request,
		templates,
		template_name="url.html",
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
	urls = [url.strip() for url in product_urls if url.strip()]
	if not urls:
		return render_web_page(
			request,
			templates,
			template_name="url.html",
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

	try:
		if len(urls) == 1:
			products = [_importing_helpers.run_import_product(urls[0])]
			errors: list[dict[str, str]] = []
		else:
			products, errors = _importing_helpers.run_import_products(urls)
	except HTTPException as exc:
		return render_web_page(
			request,
			templates,
			template_name="url.html",
			active_page="url",
			error=str(exc.detail),
			error_title="Import Error",
			product_urls=urls,
			target_platform="shopify",
			weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
			bigcommerce_csv_format="modern",
			squarespace_product_page="",
			squarespace_product_url="",
			status_code=exc.status_code,
		)

	if len(products) == 1:
		product = products[0]
		editor_payload = serialize_product_for_api(product, include_raw=False)
		return render_web_page(
			request,
			templates,
			template_name="url.html",
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
			url_import_errors=errors,
		)

	if not products:
		return render_web_page(
			request,
			templates,
			template_name="url.html",
			active_page="url",
			error="All URL imports failed.",
			error_title="Import Error",
			product_urls=urls,
			target_platform="shopify",
			weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
			bigcommerce_csv_format="modern",
			squarespace_product_page="",
			squarespace_product_url="",
			url_import_errors=errors,
			status_code=422,
		)

	editor_payloads = [serialize_product_for_api(product, include_raw=False) for product in products]
	return render_web_page(
		request,
		templates,
		template_name="url.html",
		active_page="url",
		error=None,
		error_title="Import Error",
		product_urls=urls,
		target_platform="shopify",
		weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
		bigcommerce_csv_format="modern",
		squarespace_product_page="",
		squarespace_product_url="",
		preview_product_json_b64=products_to_json_b64(products),
		editor_product_payload=None,
		editor_products_payload=editor_payloads,
		url_import_errors=errors,
	)


def _export_csv_response(
	*,
	product_urls: list[str],
	target_platform: str,
	publish: bool,
	weight_unit: str,
	bigcommerce_csv_format: str = "modern",
	squarespace_product_page: str = "",
	squarespace_product_url: str = "",
) -> Response:
	if len(product_urls) == 1:
		products = _importing_helpers.run_import_product(product_urls[0])
	else:
		products_list, errors = _importing_helpers.run_import_products(product_urls)
		if errors and not products_list:
			raise HTTPException(status_code=422, detail=errors[0]["detail"])
		products = products_list if len(products_list) > 1 else products_list[0]
	exported = export_csv(
		products,
		target=target_platform,
		options={
			"publish": publish,
			"weight_unit": weight_unit,
			"bigcommerce_csv_format": bigcommerce_csv_format,
			"squarespace_product_page": squarespace_product_page,
			"squarespace_product_url": squarespace_product_url,
		},
	)
	return Response(
		content=exported.csv_bytes,
		media_type="text/csv; charset=utf-8",
		headers={"Content-Disposition": f'attachment; filename="{exported.filename}"'},
	)


@router.post("/export/shopify.csv")
def export_shopify_csv_from_web(
	product_url: str = Form(...),
	publish: bool = Form(False),
	weight_unit: str = Form("g"),
) -> Response:
	return _export_csv_response(
		product_urls=[product_url],
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
	return _export_csv_response(
		product_urls=[product_url],
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
	return _export_csv_response(
		product_urls=[product_url],
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
	return _export_csv_response(
		product_urls=[product_url],
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
	return _export_csv_response(
		product_urls=[product_url],
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
		return _export_csv_response(
			product_urls=[product_url],
			target_platform=target_platform,
			publish=publish,
			weight_unit=weight_unit,
			bigcommerce_csv_format=bigcommerce_csv_format,
			squarespace_product_page=squarespace_product_page,
			squarespace_product_url=squarespace_product_url,
		)
	except (HTTPException, ValueError) as exc:
		detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
		status_code = exc.status_code if isinstance(exc, HTTPException) else 422
		return render_web_page(
			request,
			templates,
			template_name="url.html",
			active_page="url",
			error=detail,
			error_title="Export Error",
			product_urls=[product_url],
			target_platform=target_platform,
			weight_unit=weight_unit,
			bigcommerce_csv_format=bigcommerce_csv_format,
			squarespace_product_page=squarespace_product_page,
			squarespace_product_url=squarespace_product_url,
			status_code=status_code,
		)
