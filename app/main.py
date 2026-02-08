from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote_plus

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
 
from .config import get_settings
from .schemas import ExportShopifyCsvRequest, ImportRequest
from .services.exporters import product_to_shopify_csv
from .services.importer import ApiConfig, ProductResult, detect_product_url, fetch_product_details, requires_rapidapi

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file if present

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    summary="Product URL importer with API + web interface",
    version="1.0.0",
)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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
            detail="Unsupported URL. Supported platforms: Shopify, Amazon, Etsy, AliExpress.",
        )
    return normalized


def _run_import_product(product_url: str) -> ProductResult:
    normalized_url = _normalize_url(product_url)

    if requires_rapidapi(normalized_url) and not settings.rapidapi_key:
        raise HTTPException(
            status_code=503,
            detail="RAPIDAPI_KEY is required for Amazon, Etsy, and AliExpress imports.",
        )

    try:
        return fetch_product_details(normalized_url, _api_config())
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


def _run_import(product_url: str) -> dict:
    product = _run_import_product(product_url)
    return product.to_dict(include_raw=settings.debug)


def _shopify_csv_download_url(product_url: str, *, publish: bool = False) -> str:
    normalized_url = _normalize_url(product_url)
    publish_flag = "&publish=true" if publish else ""
    return f"/api/v1/export/shopify.csv?url={quote_plus(normalized_url)}{publish_flag}"


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


@app.get("/api/v1/export/shopify.csv")
def export_shopify_csv_from_query(
    url: str = Query(..., description="Product URL to import and convert to Shopify CSV"),
    publish: bool = Query(False, description="If true, mark product as active/published"),
) -> Response:
    product = _run_import_product(url)
    csv_text, filename = product_to_shopify_csv(product, publish=publish)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/v1/export/shopify.csv")
def export_shopify_csv_from_body(payload: ExportShopifyCsvRequest) -> Response:
    product = _run_import_product(payload.product_url)
    csv_text, filename = product_to_shopify_csv(product, publish=payload.publish)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "brand": settings,
            "result_json": None,
            "shopify_csv_url": None,
            "error": None,
            "form": {"product_url": ""},
            "examples": [
                "https://example.myshopify.com/products/sample-product",
                "https://www.amazon.com/dp/B0C1234567",
                "https://www.etsy.com/listing/123456789/sample-listing",
            ],
        },
    )


@app.post("/import", response_class=HTMLResponse)
def import_from_web(
    request: Request,
    product_url: str = Form(...),
) -> HTMLResponse:
    payload = None
    shopify_csv_url = None
    error = None
    status_code = 200
    try:
        product = _run_import_product(product_url)
        payload = product.to_dict(include_raw=settings.debug)
        shopify_csv_url = _shopify_csv_download_url(product_url)
    except HTTPException as exc:
        error = exc.detail
        status_code = exc.status_code

    result_json = json.dumps(payload, indent=2) if payload else None
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "brand": settings,
            "result_json": result_json,
            "shopify_csv_url": shopify_csv_url,
            "error": error,
            "form": {"product_url": product_url},
            "examples": [
                "https://example.myshopify.com/products/sample-product",
                "https://www.amazon.com/dp/B0C1234567",
                "https://www.etsy.com/listing/123456789/sample-listing",
            ],
        },
        status_code=status_code,
    )
