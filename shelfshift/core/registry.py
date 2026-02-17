"""Minimal registry for core importer/exporter extension points."""


from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .canonical.entities import Product

ImporterFn = Callable[..., Product | list[Product] | tuple[list[Product], list[dict[str, str]]]]
ExporterFn = Callable[..., tuple[str, str]]


@dataclass
class Registry:
    importers: dict[str, ImporterFn] = field(default_factory=dict)
    exporters: dict[str, ExporterFn] = field(default_factory=dict)

    def register_importer(self, key: str, handler: ImporterFn) -> None:
        self.importers[str(key).strip().lower()] = handler

    def register_exporter(self, key: str, handler: ExporterFn) -> None:
        self.exporters[str(key).strip().lower()] = handler

    def get_importer(self, key: str) -> ImporterFn:
        normalized = str(key).strip().lower()
        handler = self.importers.get(normalized)
        if handler is None:
            raise KeyError(f"No importer registered for key: {normalized}")
        return handler

    def get_exporter(self, key: str) -> ExporterFn:
        normalized = str(key).strip().lower()
        handler = self.exporters.get(normalized)
        if handler is None:
            raise KeyError(f"No exporter registered for key: {normalized}")
        return handler

    def list_importers(self) -> list[str]:
        return sorted(self.importers.keys())

    def list_exporters(self) -> list[str]:
        return sorted(self.exporters.keys())


_registry = Registry()


def register_importer(key: str, handler: ImporterFn) -> None:
    _registry.register_importer(key, handler)


def register_exporter(key: str, handler: ExporterFn) -> None:
    _registry.register_exporter(key, handler)


def get_importer(key: str) -> ImporterFn:
    return _registry.get_importer(key)


def get_exporter(key: str) -> ExporterFn:
    return _registry.get_exporter(key)


def list_importers() -> list[str]:
    return _registry.list_importers()


def list_exporters() -> list[str]:
    return _registry.list_exporters()


def _register_defaults() -> None:
    from .exporters import export_csv_for_target
    from .importers.csv import import_product_from_csv
    from .importers.url import import_product_from_url

    if "url" not in _registry.importers:
        _registry.register_importer("url", import_product_from_url)
    if "csv" not in _registry.importers:
        _registry.register_importer("csv", import_product_from_csv)
    for target in ("shopify", "bigcommerce", "wix", "squarespace", "woocommerce"):
        if target not in _registry.exporters:
            _registry.register_exporter(target, export_csv_for_target)


_register_defaults()


__all__ = [
    "Registry",
    "get_exporter",
    "get_importer",
    "list_exporters",
    "list_importers",
    "register_exporter",
    "register_importer",
]
