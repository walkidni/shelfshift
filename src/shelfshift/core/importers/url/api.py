from ...canonical import Product
from ...detect.url import detect_product_url
from .common import ProductClient
from .platforms.shopify import ShopifyClient
from .platforms.squarespace import SquarespaceClient
from .platforms.woocommerce import WooCommerceClient


class ProductClientFactory:
    """
    Factory that wires clients. By default:
      - Shopify: public JSON
      - Squarespace: page JSON with HTML JSON-LD fallback
      - WooCommerce: Store API with HTML JSON-LD fallback
    """

    def __init__(self):
        self._clients: dict[str, ProductClient] = {
            "shopify": ShopifyClient(),
            "squarespace": SquarespaceClient(),
            "woocommerce": WooCommerceClient(),
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


def fetch_product_details(url: str) -> Product:
    client = ProductClientFactory().for_url(url)
    return client.fetch_product(url)


def import_product(url: str) -> dict:
    product = fetch_product_details(url)
    return product.to_dict()


__all__ = [
    "ProductClientFactory",
    "fetch_product_details",
    "import_product",
]
