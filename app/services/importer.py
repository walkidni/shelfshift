from .platforms import (
    AliExpressClient,
    AmazonRapidApiClient,
    ApiConfig,
    ProductClient,
    ProductResult,
    ShopifyClient,
    Variant,
    _parse_aliexpress_result,
)
from .product_url_detection import detect_product_url


class ProductClientFactory:
    """
    Factory that wires clients. By default:
      - Shopify: public JSON
      - Amazon/AliExpress: RapidAPI (hardcoded providers)
    """

    def __init__(self, cfg: ApiConfig):
        self.cfg = cfg
        self._clients: dict[str, ProductClient] = {
            "shopify": ShopifyClient(),
            "amazon": AmazonRapidApiClient(cfg),
            "aliexpress": AliExpressClient(cfg),
        }

    def for_url(self, url: str) -> ProductClient:
        info = detect_product_url(url)
        platform = info.get("platform")
        if not platform:
            raise ValueError("Unrecognized platform for URL.")
        client = self._clients.get(platform)
        if not client:
            raise ValueError(f"No client for platform {platform}")
        return client


def fetch_product_details(url: str, cfg: ApiConfig) -> ProductResult:
    client = ProductClientFactory(cfg).for_url(url)
    return client.fetch_product(url)


def requires_rapidapi(url: str) -> bool:
    info = detect_product_url(url)
    return info.get("platform") in {"amazon", "aliexpress"}


def import_product(url: str, cfg: ApiConfig, include_raw: bool = False) -> dict:
    product = fetch_product_details(url, cfg)
    return product.to_dict(include_raw=include_raw)


__all__ = [
    "AliExpressClient",
    "AmazonRapidApiClient",
    "ApiConfig",
    "ProductClient",
    "ProductClientFactory",
    "ProductResult",
    "ShopifyClient",
    "Variant",
    "_parse_aliexpress_result",
    "detect_product_url",
    "fetch_product_details",
    "import_product",
    "requires_rapidapi",
]
