from pathlib import Path
import json
import logging

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests

from .config import get_settings
from .schemas import (
    ExportBigCommerceCsvRequest,
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


def _render_index(
    request: Request,
    *,
    error: str | None,
    product_url: str,
    target_platform: str,
    weight_unit: str,
    bigcommerce_csv_format: str,
    squarespace_product_page: str,
    squarespace_product_url: str,
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "brand": settings,
            "error": error,
            "form": {
                "product_url": product_url,
                "target_platform": target_platform,
                "weight_unit": weight_unit,
                "bigcommerce_csv_format": bigcommerce_csv_format,
                "squarespace_product_page": squarespace_product_page,
                "squarespace_product_url": squarespace_product_url,
            },
            "weight_unit_allowlist": {
                platform: list(units)
                for platform, units in WEIGHT_UNIT_ALLOWLIST_BY_TARGET.items()
            },
            "weight_unit_defaults": dict(DEFAULT_WEIGHT_UNIT_BY_TARGET),
            "examples": EXAMPLE_URLS,
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


@app.post("/api/v1/export/shopify.csv")
def export_shopify_csv_from_body(payload: ExportShopifyCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_shopify_csv(
        product,
        publish=payload.publish,
        weight_unit=payload.weight_unit,
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/api/v1/export/bigcommerce.csv")
def export_bigcommerce_csv_from_body(payload: ExportBigCommerceCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_bigcommerce_csv(
        product,
        publish=payload.publish,
        csv_format=payload.csv_format,
        weight_unit=payload.weight_unit,
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/api/v1/export/wix.csv")
def export_wix_csv_from_body(payload: ExportWixCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_wix_csv(
        product,
        publish=payload.publish,
        weight_unit=payload.weight_unit,
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/api/v1/export/squarespace.csv")
def export_squarespace_csv_from_body(payload: ExportSquarespaceCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_squarespace_csv(
        product,
        publish=payload.publish,
        product_page=payload.product_page,
        product_url=payload.squarespace_product_url,
        weight_unit=payload.weight_unit,
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/api/v1/export/woocommerce.csv")
def export_woocommerce_csv_from_body(payload: ExportWooCommerceCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_woocommerce_csv(
        product,
        publish=payload.publish,
        weight_unit=payload.weight_unit,
    )
    return _csv_attachment_response(csv_text, filename)


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return _render_index(
        request,
        error=None,
        product_url="",
        target_platform="shopify",
        weight_unit=DEFAULT_WEIGHT_UNIT_BY_TARGET["shopify"],
        bigcommerce_csv_format="modern",
        squarespace_product_page="",
        squarespace_product_url="",
    )


@app.post("/export/shopify.csv")
def export_shopify_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form("g"),
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = product_to_shopify_csv(
        product,
        publish=publish,
        weight_unit=_resolve_weight_unit_or_422("shopify", weight_unit),
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/export/bigcommerce.csv")
def export_bigcommerce_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    csv_format: str = Form("modern"),
    weight_unit: str = Form("kg"),
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = product_to_bigcommerce_csv(
        product,
        publish=publish,
        csv_format=csv_format,
        weight_unit=_resolve_weight_unit_or_422("bigcommerce", weight_unit),
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/export/wix.csv")
def export_wix_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form("kg"),
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = product_to_wix_csv(
        product,
        publish=publish,
        weight_unit=_resolve_weight_unit_or_422("wix", weight_unit),
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/export/squarespace.csv")
def export_squarespace_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    squarespace_product_page: str = Form(default=""),
    squarespace_product_url: str = Form(default=""),
    weight_unit: str = Form("kg"),
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = product_to_squarespace_csv(
        product,
        publish=publish,
        product_page=squarespace_product_page,
        product_url=squarespace_product_url,
        weight_unit=_resolve_weight_unit_or_422("squarespace", weight_unit),
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/export/woocommerce.csv")
def export_woocommerce_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    weight_unit: str = Form("kg"),
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = product_to_woocommerce_csv(
        product,
        publish=publish,
        weight_unit=_resolve_weight_unit_or_422("woocommerce", weight_unit),
    )
    return _csv_attachment_response(csv_text, filename)


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
    except HTTPException as exc:
        return _render_index(
            request,
            error=exc.detail,
            product_url=product_url,
            target_platform=target_platform,
            weight_unit=weight_unit,
            bigcommerce_csv_format=bigcommerce_csv_format,
            squarespace_product_page=squarespace_product_page,
            squarespace_product_url=squarespace_product_url,
            status_code=exc.status_code,
        )
