"""Public package entrypoint for the Shelfshift engine.

This package provides a stable import surface for core e-commerce catalog
import/export logic, plus optional frontend adapters (CLI and FastAPI server).
"""

from importlib.metadata import PackageNotFoundError, version
from typing import Any

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "convert_csv": ("shelfshift.core", "convert_csv"),
    "detect_csv": ("shelfshift.core", "detect_csv"),
    "detect_url": ("shelfshift.core", "detect_url"),
    "export_csv": ("shelfshift.core", "export_csv"),
    "import_csv": ("shelfshift.core", "import_csv"),
    "import_json": ("shelfshift.core", "import_json"),
    "import_url": ("shelfshift.core", "import_url"),
    "validate": ("shelfshift.core", "validate"),
}

try:
    __version__ = version("shelfshift")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    "convert_csv",
    "detect_csv",
    "detect_url",
    "export_csv",
    "import_csv",
    "import_json",
    "import_url",
    "validate",
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
