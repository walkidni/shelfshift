from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests

from .config import get_settings
from .schemas import ImportRequest
from .services.importer import ApiConfig, detect_product_url, import_product, requires_rapidapi

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


def _run_import(product_url: str) -> dict:
    normalized_url = _normalize_url(product_url)

    if requires_rapidapi(normalized_url) and not settings.rapidapi_key:
        raise HTTPException(
            status_code=503,
            detail="RAPIDAPI_KEY is required for Amazon, Etsy, and AliExpress imports.",
        )

    try:
        return import_product(normalized_url, _api_config(), include_raw=settings.debug)
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/v1/detect")
def detect(url: str = Query(..., description="Product URL to classify")) -> dict:
    return detect_product_url(url)


@app.post("/api/v1/import")
def import_from_api(payload: ImportRequest) -> dict:
    return _run_import(payload.product_url)


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "brand": settings,
            "result_json": None,
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
    error = None
    status_code = 200
    try:
        payload = _run_import(product_url)
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
