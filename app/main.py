from pathlib import Path
import base64
import json
import logging

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests

from .config import get_settings
from .schemas import (
    ExportBigCommerceCsvRequest,
    ExportFromProductCsvRequest,
    ExportShopifyCsvRequest,
    ExportSquarespaceCsvRequest,
    ExportWixCsvRequest,
    ExportWooCommerceCsvRequest,
    ImportRequest,
)
from .models import Product, serialize_product_for_api
from .services.exporters import (
    product_to_bigcommerce_csv,
    product_to_shopify_csv,
    product_to_squarespace_csv,
    product_to_wix_csv,
    product_to_woocommerce_csv,
)
from .services.exporters.weight_units import (
    DEFAULT_WEIGHT_UNIT_BY_TARGET,
    WEIGHT_UNIT_ALLOWLIST_BY_TARGET,
    resolve_weight_unit,
)
from .services.logging import product_result_to_loggable
from .services.csv_importers import import_product_from_csv, parse_canonical_product_payload
from .services.importer import (
    ApiConfig,
    detect_product_url,
    fetch_product_details,
    requires_rapidapi,
)

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"

settings = get_settings()
# Use Uvicorn's error logger so app logs appear in the standard server log stream.
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

_PREVIEW_DESCRIPTION_LIMIT = 320
_PREVIEW_META_DESCRIPTION_LIMIT = 200

app = FastAPI(
    title=settings.app_name,
    summary="Ingest product URLs and export importable platform CSV files",
    version="1.0.0",
)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
EXAMPLE_URLS = [
    "https://example.myshopify.com/products/sample-product",
    "https://www.amazon.com/dp/B0C1234567",
    "https://www.aliexpress.com/item/1005008518647948.html",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _api_config() -> ApiConfig:
    return ApiConfig(
        rapidapi_key=settings.rapidapi_key,
        amazon_country=settings.amazon_country,
    )


def _normalize_url(product_url: str) -> str:
    normalized = (product_url or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="product_url is required")
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"

    info = detect_product_url(normalized)
    if not info.get("platform"):
        raise HTTPException(
            status_code=422,
            detail="Unsupported URL. Supported import sources: Shopify, WooCommerce, Squarespace, Amazon, AliExpress.",
        )
    return normalized


def _run_import_product(product_url: str) -> Product:
    normalized_url = _normalize_url(product_url)

    if requires_rapidapi(normalized_url) and not settings.rapidapi_key:
        raise HTTPException(
            status_code=503,
            detail="RAPIDAPI_KEY is required for Amazon and AliExpress imports.",
        )

    try:
        product = fetch_product_details(normalized_url, _api_config())
        logger.debug(
            "Imported product summary:\n%s",
            json.dumps(product_result_to_loggable(product), ensure_ascii=False, indent=2),
        )
        return product
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", 502) or 502
        text = getattr(exc.response, "text", str(exc))
        raise HTTPException(status_code=status, detail=f"Upstream provider error: {text}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal import error: {exc}") from exc


def _run_import_csv_product(
    *,
    source_platform: str,
    csv_bytes: bytes,
    source_weight_unit: str | None,
) -> Product:
    try:
        product = import_product_from_csv(
            source_platform=source_platform,
            csv_bytes=csv_bytes,
            source_weight_unit=source_weight_unit,
        )
        logger.debug(
            "Imported CSV product summary:\n%s",
            json.dumps(product_result_to_loggable(product), ensure_ascii=False, indent=2),
        )
        return product
    except ValueError as exc:
        detail = str(exc)
        if "exceeds 5 MB" in detail:
            raise HTTPException(status_code=413, detail=detail) from exc
        raise HTTPException(status_code=422, detail=detail) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal CSV import error: {exc}") from exc


def _decode_product_json_b64(encoded: str) -> dict:
    try:
        payload = base64.b64decode(str(encoded or "").encode("utf-8"), validate=True)
        data = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid product preview payload.") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Invalid product preview payload.")
    return data


def _product_to_json_b64(product: Product) -> str:
    payload = serialize_product_for_api(product, include_raw=False)
    return base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("utf-8")


def _truncate_preview_text(value: str | None, *, limit: int) -> str | None:
    if value is None:
        return None
    if len(value) <= limit:
        return value
    return f"{value[:limit].rstrip()}... [truncated]"


def _preview_payload_for_web(product: Product) -> dict:
    payload = serialize_product_for_api(product, include_raw=False)
    preview_payload = dict(payload)

    description = preview_payload.get("description")
    if isinstance(description, str):
        preview_payload["description"] = _truncate_preview_text(
            description,
            limit=_PREVIEW_DESCRIPTION_LIMIT,
        )

    seo = preview_payload.get("seo")
    if isinstance(seo, dict):
        preview_seo = dict(seo)
        seo_description = preview_seo.get("description")
        if isinstance(seo_description, str):
            preview_seo["description"] = _truncate_preview_text(
                seo_description,
                limit=_PREVIEW_META_DESCRIPTION_LIMIT,
            )
        preview_payload["seo"] = preview_seo

    meta_description = preview_payload.get("meta_description")
    if isinstance(meta_description, str):
        preview_payload["meta_description"] = _truncate_preview_text(
            meta_description,
            limit=_PREVIEW_META_DESCRIPTION_LIMIT,
        )

    return preview_payload


def _product_from_payload_dict(payload: dict) -> Product:
    try:
        return parse_canonical_product_payload(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid product payload: {exc}") from exc


def _resolve_weight_unit_or_422(target_platform: str, weight_unit: str) -> str:
    try:
        return resolve_weight_unit(target_platform, weight_unit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _export_csv_for_target(
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


def _csv_attachment_response(csv_text: str, filename: str) -> Response:
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _export_csv_attachment_for_target(
    product_url: str,
    *,
    target_platform: str,
    publish: bool,
    weight_unit: str,
    bigcommerce_csv_format: str = "modern",
    squarespace_product_page: str = "",
    squarespace_product_url: str = "",
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = _export_csv_for_target(
        product,
        target_platform=target_platform,
        publish=publish,
        weight_unit=weight_unit,
        bigcommerce_csv_format=bigcommerce_csv_format,
        squarespace_product_page=squarespace_product_page,
        squarespace_product_url=squarespace_product_url,
    )
    return _csv_attachment_response(csv_text, filename)


def _export_csv_attachment_for_product(
    product: Product,
    *,
    target_platform: str,
    publish: bool,
    weight_unit: str,
    bigcommerce_csv_format: str = "modern",
    squarespace_product_page: str = "",
    squarespace_product_url: str = "",
) -> Response:
    csv_text, filename = _export_csv_for_target(
        product,
        target_platform=target_platform,
        publish=publish,
        weight_unit=weight_unit,
        bigcommerce_csv_format=bigcommerce_csv_format,
        squarespace_product_page=squarespace_product_page,
        squarespace_product_url=squarespace_product_url,
    )
    return _csv_attachment_response(csv_text, filename)


def _render_web_page(
    request: Request,
    *,
    template_name: str,
    active_page: str,
    error: str | None,
    product_url: str,
    target_platform: str,
    weight_unit: str,
    bigcommerce_csv_format: str,
    squarespace_product_page: str,
    squarespace_product_url: str,
    csv_source_platform: str = "shopify",
    csv_source_weight_unit: str = "kg",
    csv_error: str | None = None,
    preview_product_json: str | None = None,
    preview_product_json_b64: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template_name,
        {
            "brand": settings,
            "active_page": active_page,
            "error": error,
            "csv_error": csv_error,
            "form": {
                "product_url": product_url,
                "target_platform": target_platform,
                "weight_unit": weight_unit,
                "bigcommerce_csv_format": bigcommerce_csv_format,
                "squarespace_product_page": squarespace_product_page,
                "squarespace_product_url": squarespace_product_url,
                },
            "csv_form": {
                "source_platform": csv_source_platform,
                "source_weight_unit": csv_source_weight_unit,
            },
            "weight_unit_allowlist": {
                platform: list(units)
                for platform, units in WEIGHT_UNIT_ALLOWLIST_BY_TARGET.items()
            },
            "weight_unit_defaults": dict(DEFAULT_WEIGHT_UNIT_BY_TARGET),
            "examples": EXAMPLE_URLS,
            "source_weight_unit_allowlist": ["g", "kg", "lb", "oz"],
            "source_weight_unit_required_platforms": ["bigcommerce", "wix", "squarespace"],
            "preview_product_json": preview_product_json,
            "preview_product_json_b64": preview_product_json_b64,
        },
        status_code=status_code,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/v1/detect")
def detect(url: str = Query(..., description="Product URL to classify")) -> dict:
    return detect_product_url(url)


@app.post("/api/v1/import")
def import_from_api(payload: ImportRequest) -> dict:
    product = _run_import_product(payload.product_url)
    return serialize_product_for_api(
        product,
        include_raw=settings.debug,
    )


@app.post("/api/v1/import/csv")
def import_from_csv_api(
    source_platform: str = Form(...),
    source_weight_unit: str = Form(""),
    file: UploadFile = File(...),
) -> dict:
    csv_bytes = file.file.read()
    product = _run_import_csv_product(
        source_platform=source_platform,
        csv_bytes=csv_bytes,
        source_weight_unit=source_weight_unit,
    )
    return serialize_product_for_api(product, include_raw=settings.debug)


@app.post("/api/v1/export/from-product.csv")
def export_from_product_csv(payload: ExportFromProductCsvRequest) -> Response:
    product = _product_from_payload_dict(payload.product)
    return _export_csv_attachment_for_product(
        product,
        target_platform=payload.target_platform,
        publish=payload.publish,
        weight_unit=payload.weight_unit,
        bigcommerce_csv_format=payload.bigcommerce_csv_format,
        squarespace_product_page=payload.squarespace_product_page,
        squarespace_product_url=payload.squarespace_product_url,
    )


@app.post("/api/v1/export/shopify.csv")
def export_shopify_csv_from_body(payload: ExportShopifyCsvRequest) -> Response:
    return _export_csv_attachment_for_target(
        payload.product_url,
        target_platform="shopify",
        publish=payload.publish,
        weight_unit=payload.weight_unit,
    )


@app.post("/api/v1/export/bigcommerce.csv")
def export_bigcommerce_csv_from_body(payload: ExportBigCommerceCsvRequest) -> Response:
    return _export_csv_attachment_for_target(
        payload.product_url,
        target_platform="bigcommerce",
        publish=payload.publish,
        weight_unit=payload.weight_unit,
        bigcommerce_csv_format=payload.csv_format,
    )


@app.post("/api/v1/export/wix.csv")
def export_wix_csv_from_body(payload: ExportWixCsvRequest) -> Response:
    return _export_csv_attachment_for_target(
        payload.product_url,
        target_platform="wix",
        publish=payload.publish,
        weight_unit=payload.weight_unit,
    )


@app.post("/api/v1/export/squarespace.csv")
def export_squarespace_csv_from_body(payload: ExportSquarespaceCsvRequest) -> Response:
    return _export_csv_attachment_for_target(
        payload.product_url,
        target_platform="squarespace",
        publish=payload.publish,
        weight_unit=payload.weight_unit,
        squarespace_product_page=payload.product_page,
        squarespace_product_url=payload.squarespace_product_url,
    )


@app.post("/api/v1/export/woocommerce.csv")
def export_woocommerce_csv_from_body(payload: ExportWooCommerceCsvRequest) -> Response:
    return _export_csv_attachment_for_target(
        payload.product_url,
        target_platform="woocommerce",
        publish=payload.publish,
        weight_unit=payload.weight_unit,
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return _render_web_page(
        request,
        template_name="index.html",
        active_page="url",
        error=None,
        product_url="",
        target_platform="shopify",
        weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
        bigcommerce_csv_format="modern",
        squarespace_product_page="",
        squarespace_product_url="",
    )


@app.get("/csv", response_class=HTMLResponse)
def csv_home(request: Request) -> HTMLResponse:
    return _render_web_page(
        request,
        template_name="csv.html",
        active_page="csv",
        error=None,
        product_url="",
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


@app.post("/export/shopify.csv")
def export_shopify_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form("g"),
) -> Response:
    return _export_csv_attachment_for_target(
        product_url,
        target_platform="shopify",
        publish=publish,
        weight_unit=weight_unit,
    )


@app.post("/export/bigcommerce.csv")
def export_bigcommerce_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    csv_format: str = Form("modern"),
    weight_unit: str = Form("kg"),
) -> Response:
    return _export_csv_attachment_for_target(
        product_url,
        target_platform="bigcommerce",
        publish=publish,
        weight_unit=weight_unit,
        bigcommerce_csv_format=csv_format,
    )


@app.post("/export/wix.csv")
def export_wix_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form("kg"),
) -> Response:
    return _export_csv_attachment_for_target(
        product_url,
        target_platform="wix",
        publish=publish,
        weight_unit=weight_unit,
    )


@app.post("/export/squarespace.csv")
def export_squarespace_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    squarespace_product_page: str = Form(default=""),
    squarespace_product_url: str = Form(default=""),
    weight_unit: str = Form("kg"),
) -> Response:
    return _export_csv_attachment_for_target(
        product_url,
        target_platform="squarespace",
        publish=publish,
        weight_unit=weight_unit,
        squarespace_product_page=squarespace_product_page,
        squarespace_product_url=squarespace_product_url,
    )


@app.post("/export/woocommerce.csv")
def export_woocommerce_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form("kg"),
) -> Response:
    return _export_csv_attachment_for_target(
        product_url,
        target_platform="woocommerce",
        publish=publish,
        weight_unit=weight_unit,
    )


@app.post("/import.csv")
def import_csv_from_web(
    request: Request,
    source_platform: str = Form(...),
    source_weight_unit: str = Form(default=""),
    file: UploadFile = File(...),
) -> HTMLResponse:
    try:
        csv_bytes = file.file.read()
        product = _run_import_csv_product(
            source_platform=source_platform,
            csv_bytes=csv_bytes,
            source_weight_unit=source_weight_unit,
        )
        preview_payload = _preview_payload_for_web(product)
        preview_json = json.dumps(preview_payload, ensure_ascii=False, indent=2)
        return _render_web_page(
            request,
            template_name="csv.html",
            active_page="csv",
            error=None,
            product_url="",
            target_platform="shopify",
            weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
            bigcommerce_csv_format="modern",
            squarespace_product_page="",
            squarespace_product_url="",
            csv_source_platform=source_platform,
            csv_source_weight_unit=source_weight_unit or "kg",
            preview_product_json=preview_json,
            preview_product_json_b64=_product_to_json_b64(product),
        )
    except HTTPException as exc:
        return _render_web_page(
            request,
            template_name="csv.html",
            active_page="csv",
            error=None,
            csv_error=exc.detail,
            product_url="",
            target_platform="shopify",
            weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
            bigcommerce_csv_format="modern",
            squarespace_product_page="",
            squarespace_product_url="",
            csv_source_platform=source_platform,
            csv_source_weight_unit=source_weight_unit or "kg",
            status_code=exc.status_code,
        )


@app.post("/export-from-product.csv")
def export_from_product_csv_web(
    product_json_b64: str = Form(...),
    target_platform: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form(default=""),
    bigcommerce_csv_format: str = Form("modern"),
    squarespace_product_page: str = Form(default=""),
    squarespace_product_url: str = Form(default=""),
) -> Response:
    payload = _decode_product_json_b64(product_json_b64)
    product = _product_from_payload_dict(payload)
    return _export_csv_attachment_for_product(
        product,
        target_platform=target_platform,
        publish=publish,
        weight_unit=weight_unit,
        bigcommerce_csv_format=bigcommerce_csv_format,
        squarespace_product_page=squarespace_product_page,
        squarespace_product_url=squarespace_product_url,
    )


@app.post("/export.csv")
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
        return _export_csv_attachment_for_target(
            product_url,
            target_platform=target_platform,
            publish=publish,
            weight_unit=weight_unit,
            bigcommerce_csv_format=bigcommerce_csv_format,
            squarespace_product_page=squarespace_product_page,
            squarespace_product_url=squarespace_product_url,
        )
    except HTTPException as exc:
        return _render_web_page(
            request,
            template_name="index.html",
            active_page="url",
            error=exc.detail,
            product_url=product_url,
            target_platform=target_platform,
            weight_unit=weight_unit,
            bigcommerce_csv_format=bigcommerce_csv_format,
            squarespace_product_page=squarespace_product_page,
            squarespace_product_url=squarespace_product_url,
            status_code=exc.status_code,
        )
