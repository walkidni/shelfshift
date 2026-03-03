from __future__ import annotations

import shelfshift.core as core


_EXPECTED_CORE_FACADE_EXPORTS = {
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
}

_REMOVED_LOW_LEVEL_EXPORTS = {
    "CoreConfig",
    "DetectResult",
    "ExportResult",
    "ImportResult",
    "Product",
    "config_from_env",
    "detect_csv_platform",
    "detect_product_url",
    "export_csv_for_target",
    "get_exporter",
    "get_importer",
    "import_product_from_csv",
    "import_product_from_url",
    "import_products_from_csv",
    "import_products_from_urls",
    "list_exporters",
    "list_importers",
    "register_exporter",
    "register_importer",
}


def test_core_facade_exports_curated_surface() -> None:
    assert set(core.__all__) == _EXPECTED_CORE_FACADE_EXPORTS
    assert set(core._LAZY_EXPORTS) == _EXPECTED_CORE_FACADE_EXPORTS


def test_core_facade_does_not_export_low_level_helpers() -> None:
    for name in _REMOVED_LOW_LEVEL_EXPORTS:
        assert name not in core.__all__
        assert name not in core._LAZY_EXPORTS
        try:
            _ = getattr(core, name)
        except AttributeError:
            pass
        else:
            raise AssertionError(f"shelfshift.core.{name} should not be exported")
