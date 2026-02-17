"""JSON API routes: /health, /api/v1/*."""


from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.helpers import importing as _legacy_importing

from ...core.api import detect_csv, detect_url, export_csv, import_csv, parse_product_payload
from ..schemas import (
	ExportBigCommerceCsvRequest,
	ExportFromProductCsvRequest,
	ExportShopifyCsvRequest,
	ExportSquarespaceCsvRequest,
	ExportWixCsvRequest,
	ExportWooCommerceCsvRequest,
	ImportRequest,
)
from ...core.canonical.serialization import serialize_product_for_api
from ..config import get_settings

settings = get_settings()
router = APIRouter()


@router.get("/health")
def health() -> dict:
	return {"status": "ok", "app": settings.app_name}


@router.get("/api/v1/detect")
def detect(url: str = Query(..., description="Product URL to classify")) -> dict:
	result = detect_url(url)
	return {
		"platform": result.platform,
		"is_product": result.is_product,
		"product_id": result.product_id,
		"slug": result.slug,
	}


@router.post("/api/v1/import")
def import_from_api(payload: ImportRequest) -> Any:
	urls = [url.strip() for url in payload.urls_list if url.strip()]
	if not urls:
		raise HTTPException(status_code=400, detail="product_urls is required")

	if len(urls) == 1:
		product = _legacy_importing.run_import_product(urls[0])
		return serialize_product_for_api(product, include_raw=settings.debug)

	products, errors = _legacy_importing.run_import_products(urls)

	return {
		"products": [serialize_product_for_api(product, include_raw=settings.debug) for product in products],
		"errors": errors,
	}


@router.post("/api/v1/detect/csv")
def detect_csv_platform_api(
	file: UploadFile = File(...),
) -> dict:
	csv_bytes = file.file.read()
	try:
		result = detect_csv(csv_bytes)
	except ValueError as exc:
		raise HTTPException(status_code=422, detail=str(exc)) from exc
	return {"platform": result.platform}


@router.post("/api/v1/import/csv")
def import_from_csv_api(
	source_platform: str = Form(...),
	source_weight_unit: str = Form(""),
	file: UploadFile = File(...),
) -> dict | list[dict]:
	csv_bytes = file.file.read()
	try:
		result = import_csv(
			csv_bytes,
			platform=source_platform,
			source_weight_unit=source_weight_unit,
		)
	except ValueError as exc:
		detail = str(exc)
		if "exceeds 5 MB" in detail:
			raise HTTPException(status_code=413, detail=detail) from exc
		raise HTTPException(status_code=422, detail=detail) from exc

	if len(result.products) == 1:
		return serialize_product_for_api(result.products[0], include_raw=settings.debug)
	return [serialize_product_for_api(product, include_raw=settings.debug) for product in result.products]


def _export_response_from_products(
	products: Any,
	*,
	target_platform: str,
	publish: bool,
	weight_unit: str,
	bigcommerce_csv_format: str = "modern",
	squarespace_product_page: str = "",
	squarespace_product_url: str = "",
) -> Response:
	try:
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
	except ValueError as exc:
		raise HTTPException(status_code=422, detail=str(exc)) from exc
	return Response(
		content=exported.csv_bytes,
		media_type="text/csv; charset=utf-8",
		headers={"Content-Disposition": f'attachment; filename="{exported.filename}"'},
	)


@router.post("/api/v1/export/from-product.csv")
def export_from_product_csv(payload: ExportFromProductCsvRequest) -> Response:
	products = parse_product_payload(payload.product)
	return _export_response_from_products(
		products,
		target_platform=payload.target_platform,
		publish=payload.publish,
		weight_unit=payload.weight_unit,
		bigcommerce_csv_format=payload.bigcommerce_csv_format,
		squarespace_product_page=payload.squarespace_product_page,
		squarespace_product_url=payload.squarespace_product_url,
	)


@router.post("/api/v1/export/shopify.csv")
def export_shopify_csv_from_body(payload: ExportShopifyCsvRequest) -> Response:
	product = parse_product_payload(payload.product)
	return _export_response_from_products(
		product,
		target_platform="shopify",
		publish=payload.publish,
		weight_unit=payload.weight_unit,
	)


@router.post("/api/v1/export/bigcommerce.csv")
def export_bigcommerce_csv_from_body(payload: ExportBigCommerceCsvRequest) -> Response:
	product = parse_product_payload(payload.product)
	return _export_response_from_products(
		product,
		target_platform="bigcommerce",
		publish=payload.publish,
		weight_unit=payload.weight_unit,
		bigcommerce_csv_format=payload.csv_format,
	)


@router.post("/api/v1/export/wix.csv")
def export_wix_csv_from_body(payload: ExportWixCsvRequest) -> Response:
	product = parse_product_payload(payload.product)
	return _export_response_from_products(
		product,
		target_platform="wix",
		publish=payload.publish,
		weight_unit=payload.weight_unit,
	)


@router.post("/api/v1/export/squarespace.csv")
def export_squarespace_csv_from_body(payload: ExportSquarespaceCsvRequest) -> Response:
	product = parse_product_payload(payload.product)
	return _export_response_from_products(
		product,
		target_platform="squarespace",
		publish=payload.publish,
		weight_unit=payload.weight_unit,
		squarespace_product_page=payload.product_page,
		squarespace_product_url=payload.squarespace_product_url,
	)


@router.post("/api/v1/export/woocommerce.csv")
def export_woocommerce_csv_from_body(payload: ExportWooCommerceCsvRequest) -> Response:
	product = parse_product_payload(payload.product)
	return _export_response_from_products(
		product,
		target_platform="woocommerce",
		publish=payload.publish,
		weight_unit=payload.weight_unit,
	)
