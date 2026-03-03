"""URL-based importers."""

from ...canonical import Product
from ...config import resolve_rapidapi_key
from ...detect.url import detect_product_url as _detect_product_url
from .api import fetch_product_details as _fetch_product_details
from .api import requires_rapidapi as _requires_rapidapi
from .common import ApiConfig as _ApiConfig


def normalize_product_url(product_url: str) -> str:
    normalized = (product_url or "").strip()
    if not normalized:
        raise ValueError("product_url is required")
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"

    info = _detect_product_url(normalized)
    if not info.get("platform"):
        raise ValueError(
            "Unsupported URL. Supported import sources: Shopify, WooCommerce, Squarespace, Amazon, AliExpress."
        )
    return normalized


def import_product_from_url(
    product_url: str,
    *,
    rapidapi_key: str | None = None,
) -> Product:
    normalized_url = normalize_product_url(product_url)
    resolved_rapidapi_key = resolve_rapidapi_key(rapidapi_key)

    if requires_rapidapi(normalized_url) and not resolved_rapidapi_key:
        raise ValueError("RAPIDAPI_KEY is required for Amazon and AliExpress imports.")

    return _fetch_product_details(
        normalized_url,
        _ApiConfig(rapidapi_key=resolved_rapidapi_key),
    )


def import_products_from_urls(
    urls: list[str],
    *,
    rapidapi_key: str | None = None,
) -> tuple[list[Product], list[dict[str, str]]]:
    products: list[Product] = []
    errors: list[dict[str, str]] = []
    for url in urls:
        try:
            products.append(import_product_from_url(url, rapidapi_key=rapidapi_key))
        except ValueError as exc:
            errors.append({"url": url, "detail": str(exc)})
        except Exception as exc:
            errors.append({"url": url, "detail": f"Internal import error: {exc}"})
    return products, errors


def requires_rapidapi(url: str) -> bool:
    return _requires_rapidapi(url)


__all__ = [
    "import_product_from_url",
    "import_products_from_urls",
    "normalize_product_url",
    "requires_rapidapi",
]
