"""Public package entrypoint for the Typeshift engine.

This package provides a stable import surface for core e-commerce catalog
import/export logic, plus optional frontend adapters (CLI and FastAPI server).
"""

from importlib.metadata import PackageNotFoundError, version
from typing import Any

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "Product": ("typeshift.core", "Product"),
    "app": ("typeshift.server.main", "app"),
    "create_app": ("typeshift.server.main", "create_app"),
    "detect_csv_platform": ("typeshift.core", "detect_csv_platform"),
    "detect_product_url": ("typeshift.core", "detect_product_url"),
    "export_csv_for_target": ("typeshift.core", "export_csv_for_target"),
    "import_product_from_csv": ("typeshift.core", "import_product_from_csv"),
    "import_product_from_url": ("typeshift.core", "import_product_from_url"),
}

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


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = target
    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
