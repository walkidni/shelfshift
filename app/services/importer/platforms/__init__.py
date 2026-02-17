"""Compatibility facade for legacy ``app.services.importer.platforms`` imports."""

from shelfshift.core.importers.url.platforms import (
    AliExpressClient,
    AmazonRapidApiClient,
    ApiConfig,
    Product,
    ProductClient,
    SquarespaceClient,
    ShopifyClient,
    Variant,
    WooCommerceClient,
    _parse_aliexpress_result,
)

__all__ = [
    "AliExpressClient",
    "AmazonRapidApiClient",
    "ApiConfig",
    "ProductClient",
    "Product",
    "SquarespaceClient",
    "ShopifyClient",
    "Variant",
    "WooCommerceClient",
    "_parse_aliexpress_result",
]
