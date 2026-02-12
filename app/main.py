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
from .services.exporters import (
    product_to_bigcommerce_csv,
    product_to_shopify_csv,
    product_to_squarespace_csv,
    product_to_wix_csv,
    product_to_woocommerce_csv,
)
from .services.logging import product_result_to_loggable
from .services.importer import (
    ApiConfig,
    ProductResult,
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


def _run_import_product(product_url: str) -> ProductResult:
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


def _export_csv_for_target(
    product: ProductResult,
    *,
    target_platform: str,
    publish: bool,
    bigcommerce_csv_format: str,
    squarespace_product_page: str,
    squarespace_product_url: str,
) -> tuple[str, str]:
    target = (target_platform or "").strip().lower()
    if target == "shopify":
        return product_to_shopify_csv(product, publish=publish)
    if target == "bigcommerce":
        return product_to_bigcommerce_csv(product, publish=publish, csv_format=bigcommerce_csv_format)
    if target == "wix":
        return product_to_wix_csv(product, publish=publish)
    if target == "squarespace":
        return product_to_squarespace_csv(
            product,
            publish=publish,
            product_page=squarespace_product_page,
            product_url=squarespace_product_url,
        )
    if target == "woocommerce":
        return product_to_woocommerce_csv(product, publish=publish)

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
                "bigcommerce_csv_format": bigcommerce_csv_format,
                "squarespace_product_page": squarespace_product_page,
                "squarespace_product_url": squarespace_product_url,
            },
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
    return product.to_dict(include_raw=settings.debug)


@app.post("/api/v1/export/shopify.csv")
def export_shopify_csv_from_body(payload: ExportShopifyCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_shopify_csv(product, publish=payload.publish)
    return _csv_attachment_response(csv_text, filename)


@app.post("/api/v1/export/bigcommerce.csv")
def export_bigcommerce_csv_from_body(payload: ExportBigCommerceCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_bigcommerce_csv(
        product,
        publish=payload.publish,
        csv_format=payload.csv_format,
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/api/v1/export/wix.csv")
def export_wix_csv_from_body(payload: ExportWixCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_wix_csv(product, publish=payload.publish)
    return _csv_attachment_response(csv_text, filename)


@app.post("/api/v1/export/squarespace.csv")
def export_squarespace_csv_from_body(payload: ExportSquarespaceCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_squarespace_csv(
        product,
        publish=payload.publish,
        product_page=payload.product_page,
        product_url=payload.squarespace_product_url,
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/api/v1/export/woocommerce.csv")
def export_woocommerce_csv_from_body(payload: ExportWooCommerceCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_woocommerce_csv(product, publish=payload.publish)
    return _csv_attachment_response(csv_text, filename)


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return _render_index(
        request,
        error=None,
        product_url="",
        target_platform="shopify",
        bigcommerce_csv_format="modern",
        squarespace_product_page="",
        squarespace_product_url="",
    )


@app.post("/export/shopify.csv")
def export_shopify_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = product_to_shopify_csv(product, publish=publish)
    return _csv_attachment_response(csv_text, filename)


@app.post("/export/bigcommerce.csv")
def export_bigcommerce_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    csv_format: str = Form("modern"),
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = product_to_bigcommerce_csv(product, publish=publish, csv_format=csv_format)
    return _csv_attachment_response(csv_text, filename)


@app.post("/export/wix.csv")
def export_wix_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = product_to_wix_csv(product, publish=publish)
    return _csv_attachment_response(csv_text, filename)


@app.post("/export/squarespace.csv")
def export_squarespace_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
    squarespace_product_page: str = Form(default=""),
    squarespace_product_url: str = Form(default=""),
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = product_to_squarespace_csv(
        product,
        publish=publish,
        product_page=squarespace_product_page,
        product_url=squarespace_product_url,
    )
    return _csv_attachment_response(csv_text, filename)


@app.post("/export/woocommerce.csv")
def export_woocommerce_csv_from_web(
    product_url: str = Form(...),
    publish: bool = Form(False),
) -> Response:
    product = _run_import_product(product_url)
    csv_text, filename = product_to_woocommerce_csv(product, publish=publish)
    return _csv_attachment_response(csv_text, filename)


@app.post("/export.csv")
def export_csv_from_web(
    request: Request,
    product_url: str = Form(...),
    target_platform: str = Form(...),
    publish: bool = Form(False),
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
            bigcommerce_csv_format=bigcommerce_csv_format,
            squarespace_product_page=squarespace_product_page,
            squarespace_product_url=squarespace_product_url,
            status_code=exc.status_code,
        )
