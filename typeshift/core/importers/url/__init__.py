"""URL-based importers."""

import os

from ...canonical import Product
from .api import (
    AliExpressClient,
    AmazonRapidApiClient,
    ApiConfig,
    Media,
    Money,
    Price,
    ProductClient,
    ProductClientFactory,
    SquarespaceClient,
    ShopifyClient,
    Variant,
    Weight,
    WooCommerceClient,
    _parse_aliexpress_result,
    detect_product_url,
    fetch_product_details,
    format_decimal,
    import_product,
    normalize_currency,
    parse_decimal_money,
    requires_rapidapi,
)


def normalize_product_url(product_url: str) -> str:
    normalized = (product_url or "").strip()
    if not normalized:
        raise ValueError("product_url is required")
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"

    info = detect_product_url(normalized)
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
    resolved_rapidapi_key = rapidapi_key if rapidapi_key is not None else os.getenv("RAPIDAPI_KEY")

    if requires_rapidapi(normalized_url) and not resolved_rapidapi_key:
        raise ValueError("RAPIDAPI_KEY is required for Amazon and AliExpress imports.")

    return fetch_product_details(
        normalized_url,
        ApiConfig(rapidapi_key=resolved_rapidapi_key),
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


__all__ = [
    "AliExpressClient",
    "AmazonRapidApiClient",
    "ApiConfig",
    "Media",
    "Money",
    "Price",
    "Product",
    "ProductClient",
    "ProductClientFactory",
    "SquarespaceClient",
    "ShopifyClient",
    "Variant",
    "Weight",
    "WooCommerceClient",
    "_parse_aliexpress_result",
    "detect_product_url",
    "fetch_product_details",
    "format_decimal",
    "import_product",
    "import_product_from_url",
    "import_products_from_urls",
    "normalize_currency",
    "normalize_product_url",
    "parse_decimal_money",
    "requires_rapidapi",
]
