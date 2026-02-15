"""Web page rendering helper."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import get_settings
from ..services.exporters.weight_units import (
    DEFAULT_WEIGHT_UNIT_BY_TARGET,
    WEIGHT_UNIT_ALLOWLIST_BY_TARGET,
)

settings = get_settings()

EXAMPLE_URLS = [
    "https://example.myshopify.com/products/sample-product",
    "https://www.amazon.com/dp/B0C1234567",
    "https://www.aliexpress.com/item/1005008518647948.html",
]


def render_web_page(
    request: Request,
    templates: Jinja2Templates,
    *,
    template_name: str,
    active_page: str,
    error: str | None,
    error_title: str = "Error",
    product_urls: list[str] | None = None,
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
    editor_product_payload: dict | None = None,
    editor_products_payload: list[dict] | None = None,
    url_import_errors: list[dict[str, str]] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    urls = product_urls if product_urls else [""]
    return templates.TemplateResponse(
        request,
        template_name,
        {
            "brand": settings,
            "active_page": active_page,
            "error": error,
            "error_title": error_title,
            "csv_error": csv_error,
            "form": {
                "product_urls": urls,
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
            "editor_product_payload": editor_product_payload,
            "editor_products_payload": editor_products_payload or [],
            "url_import_errors": url_import_errors or [],
        },
        status_code=status_code,
    )
