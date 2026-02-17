"""Core engine API.

The core layer is framework-agnostic and safe to import from scripts, tests,
CLI commands, and web frontends.
"""

from typing import Any

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "CoreConfig": ("typeshift.core.config", "CoreConfig"),
    "DetectResult": ("typeshift.core.api", "DetectResult"),
    "ExportResult": ("typeshift.core.api", "ExportResult"),
    "ImportResult": ("typeshift.core.api", "ImportResult"),
    "Product": ("typeshift.core.canonical.entities", "Product"),
    "config_from_env": ("typeshift.core.config", "config_from_env"),
    "convert_csv": ("typeshift.core.api", "convert_csv"),
    "detect_csv": ("typeshift.core.api", "detect_csv"),
    "detect_csv_platform": ("typeshift.core.detect.csv", "detect_csv_platform"),
    "detect_product_url": ("typeshift.core.detect.url", "detect_product_url"),
    "detect_url": ("typeshift.core.api", "detect_url"),
    "export_csv": ("typeshift.core.api", "export_csv"),
    "export_csv_for_target": ("typeshift.core.exporters", "export_csv_for_target"),
    "get_exporter": ("typeshift.core.registry", "get_exporter"),
    "get_importer": ("typeshift.core.registry", "get_importer"),
    "import_csv": ("typeshift.core.api", "import_csv"),
    "import_product_from_csv": ("typeshift.core.importers.csv", "import_product_from_csv"),
    "import_product_from_url": ("typeshift.core.importers.url", "import_product_from_url"),
    "import_products_from_csv": ("typeshift.core.importers.csv", "import_products_from_csv"),
    "import_products_from_urls": ("typeshift.core.importers.url", "import_products_from_urls"),
    "import_url": ("typeshift.core.api", "import_url"),
    "list_exporters": ("typeshift.core.registry", "list_exporters"),
    "list_importers": ("typeshift.core.registry", "list_importers"),
    "register_exporter": ("typeshift.core.registry", "register_exporter"),
    "register_importer": ("typeshift.core.registry", "register_importer"),
    "validate": ("typeshift.core.api", "validate"),
}

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


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = target
    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
