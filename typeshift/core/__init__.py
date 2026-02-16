"""Core engine API.

The core layer is framework-agnostic and safe to import from scripts, tests,
CLI commands, and web frontends.
"""

from .api import (
    DetectResult,
    ExportResult,
    ImportResult,
    convert_csv,
    detect_csv,
    detect_url,
    export_csv,
    import_csv,
    import_url,
    validate,
)
from .canonical.entities import Product
from .config import CoreConfig, config_from_env
from .detect.csv import detect_csv_platform
from .detect.url import detect_product_url
from .exporters import export_csv_for_target
from .importers.csv import import_product_from_csv, import_products_from_csv
from .importers.url import import_product_from_url, import_products_from_urls
from .registry import (
    get_exporter,
    get_importer,
    list_exporters,
    list_importers,
    register_exporter,
    register_importer,
)

__all__ = [
    "CoreConfig",
    "DetectResult",
    "ExportResult",
    "ImportResult",
    "Product",
    "config_from_env",
    "convert_csv",
    "detect_csv",
    "detect_csv_platform",
    "detect_url",
    "detect_product_url",
    "export_csv",
    "export_csv_for_target",
    "get_exporter",
    "get_importer",
    "import_csv",
    "import_product_from_csv",
    "import_product_from_url",
    "import_products_from_csv",
    "import_products_from_urls",
    "import_url",
    "list_exporters",
    "list_importers",
    "register_exporter",
    "register_importer",
    "validate",
]
