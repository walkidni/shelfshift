"""URL-based importers."""

from ...canonical import Product
from ...detect.url import detect_product_url as _detect_product_url
from .api import fetch_product_details as _fetch_product_details

_SUPPORTED_URL_IMPORT_PLATFORMS = {"shopify", "woocommerce", "squarespace"}


def normalize_product_url(product_url: str) -> str:
    normalized = (product_url or "").strip()
    if not normalized:
        raise ValueError("product_url is required")
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"

    info = _detect_product_url(normalized)
    platform = str(info.get("platform") or "").strip().lower()
    if not platform:
        raise ValueError(
            "Unsupported URL. Supported URL detection sources: Shopify, WooCommerce, Squarespace, Amazon, AliExpress."
        )
    if platform not in _SUPPORTED_URL_IMPORT_PLATFORMS:
        raise ValueError(
            "Unsupported URL import source. Supported URL import sources: Shopify, WooCommerce, Squarespace."
        )
    return normalized


def import_product_from_url(product_url: str) -> Product:
    normalized_url = normalize_product_url(product_url)
    return _fetch_product_details(normalized_url)


def import_products_from_urls(urls: list[str]) -> tuple[list[Product], list[dict[str, str]]]:
    products: list[Product] = []
    errors: list[dict[str, str]] = []
    for url in urls:
        try:
            products.append(import_product_from_url(url))
        except ValueError as exc:
            errors.append({"url": url, "detail": str(exc)})
        except Exception as exc:
            errors.append({"url": url, "detail": f"Internal import error: {exc}"})
    return products, errors


__all__ = [
    "import_product_from_url",
    "import_products_from_urls",
    "normalize_product_url",
]
