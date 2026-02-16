"""Public package entrypoint for the Typeshift engine.

This package provides a stable import surface for core e-commerce catalog
import/export logic, plus optional frontend adapters (CLI and FastAPI server).
"""

from importlib.metadata import PackageNotFoundError, version

from .core import (
    Product,
    detect_csv_platform,
    detect_product_url,
    export_csv_for_target,
    import_product_from_csv,
    import_product_from_url,
)
from .server.main import app, create_app

try:
    __version__ = version("ecom-catalog-transfer")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "Product",
    "__version__",
    "app",
    "create_app",
    "detect_csv_platform",
    "detect_product_url",
    "export_csv_for_target",
    "import_product_from_csv",
    "import_product_from_url",
]
