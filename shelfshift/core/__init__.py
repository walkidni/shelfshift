"""Core engine API.

The core layer is framework-agnostic and safe to import from scripts, tests,
CLI commands, and web frontends.
"""

from typing import Any

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "convert_csv": ("shelfshift.core.api", "convert_csv"),
    "detect_csv": ("shelfshift.core.api", "detect_csv"),
    "detect_url": ("shelfshift.core.api", "detect_url"),
    "export_csv": ("shelfshift.core.api", "export_csv"),
    "import_csv": ("shelfshift.core.api", "import_csv"),
    "import_json": ("shelfshift.core.api", "import_json"),
    "import_url": ("shelfshift.core.api", "import_url"),
    "json_to_product": ("shelfshift.core.canonical.io", "json_to_product"),
    "json_to_products": ("shelfshift.core.canonical.io", "json_to_products"),
    "validate": ("shelfshift.core.api", "validate"),
}

__all__ = [
    "convert_csv",
    "detect_csv",
    "detect_url",
    "export_csv",
    "import_csv",
    "import_json",
    "import_url",
    "json_to_product",
    "json_to_products",
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
