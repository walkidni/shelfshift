from ...canonical import Product
from .batch import parse_shopify_csv_batch


def parse_shopify_csv(csv_text: str) -> Product:
    products = parse_shopify_csv_batch(csv_text, source_platform="shopify")
    return products[0]
