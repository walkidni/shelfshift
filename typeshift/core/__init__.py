"""Core engine API.

The core layer is framework-agnostic and safe to import from scripts, tests,
CLI commands, and web frontends.
"""

from .canonical.entities import Product
from .detect.csv import detect_csv_platform
from .detect.url import detect_product_url
from .exporters import export_csv_for_target
from .importers.csv import import_product_from_csv, import_products_from_csv
from .importers.url import import_product_from_url, import_products_from_urls

__all__ = [
    "Product",
    "detect_csv_platform",
    "detect_product_url",
    "export_csv_for_target",
    "import_product_from_csv",
    "import_product_from_url",
    "import_products_from_csv",
    "import_products_from_urls",
]
