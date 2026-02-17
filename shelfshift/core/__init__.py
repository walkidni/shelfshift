"""Core engine API.

The core layer is framework-agnostic and safe to import from scripts, tests,
CLI commands, and web frontends.
"""

from typing import Any

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "CoreConfig": ("shelfshift.core.config", "CoreConfig"),
    "DetectResult": ("shelfshift.core.api", "DetectResult"),
    "ExportResult": ("shelfshift.core.api", "ExportResult"),
    "ImportResult": ("shelfshift.core.api", "ImportResult"),
    "Product": ("shelfshift.core.canonical.entities", "Product"),
    "config_from_env": ("shelfshift.core.config", "config_from_env"),
    "convert_csv": ("shelfshift.core.api", "convert_csv"),
    "detect_csv": ("shelfshift.core.api", "detect_csv"),
    "detect_csv_platform": ("shelfshift.core.detect.csv", "detect_csv_platform"),
    "detect_product_url": ("shelfshift.core.detect.url", "detect_product_url"),
    "detect_url": ("shelfshift.core.api", "detect_url"),
    "export_csv": ("shelfshift.core.api", "export_csv"),
    "export_csv_for_target": ("shelfshift.core.exporters", "export_csv_for_target"),
    "get_exporter": ("shelfshift.core.registry", "get_exporter"),
    "get_importer": ("shelfshift.core.registry", "get_importer"),
    "import_csv": ("shelfshift.core.api", "import_csv"),
    "import_product_from_csv": ("shelfshift.core.importers.csv", "import_product_from_csv"),
    "import_product_from_url": ("shelfshift.core.importers.url", "import_product_from_url"),
    "import_products_from_csv": ("shelfshift.core.importers.csv", "import_products_from_csv"),
    "import_products_from_urls": ("shelfshift.core.importers.url", "import_products_from_urls"),
    "import_url": ("shelfshift.core.api", "import_url"),
    "list_exporters": ("shelfshift.core.registry", "list_exporters"),
    "list_importers": ("shelfshift.core.registry", "list_importers"),
    "register_exporter": ("shelfshift.core.registry", "register_exporter"),
    "register_importer": ("shelfshift.core.registry", "register_importer"),
    "validate": ("shelfshift.core.api", "validate"),
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
