from __future__ import annotations

import shelfshift
import shelfshift.core as core


_CONVENIENCE_EXPORTS = (
    "detect_url",
    "detect_csv",
    "import_url",
    "import_csv",
    "import_json",
    "export_csv",
    "convert_csv",
    "validate",
)


def test_facade_exposes_convenience_core_functions() -> None:
    for name in _CONVENIENCE_EXPORTS:
        assert name in shelfshift.__all__
        assert name in shelfshift._LAZY_EXPORTS
        assert shelfshift._LAZY_EXPORTS[name][0] == "shelfshift.core"


def test_facade_convenience_exports_resolve_to_core_callables() -> None:
    for name in _CONVENIENCE_EXPORTS:
        assert getattr(shelfshift, name) is getattr(core, name)


def test_facade_does_not_export_import_product_from_url() -> None:
    assert "import_product_from_url" not in shelfshift.__all__
    assert "import_product_from_url" not in shelfshift._LAZY_EXPORTS
    try:
        _ = shelfshift.import_product_from_url
    except AttributeError:
        pass
    else:
        raise AssertionError("shelfshift.import_product_from_url should not be exported")


def test_facade_does_not_export_import_product_from_csv() -> None:
    assert "import_product_from_csv" not in shelfshift.__all__
    assert "import_product_from_csv" not in shelfshift._LAZY_EXPORTS
    try:
        _ = shelfshift.import_product_from_csv
    except AttributeError:
        pass
    else:
        raise AssertionError("shelfshift.import_product_from_csv should not be exported")


def test_facade_does_not_export_detect_product_url() -> None:
    assert "detect_product_url" not in shelfshift.__all__
    assert "detect_product_url" not in shelfshift._LAZY_EXPORTS
    try:
        _ = shelfshift.detect_product_url
    except AttributeError:
        pass
    else:
        raise AssertionError("shelfshift.detect_product_url should not be exported")


def test_facade_does_not_export_detect_csv_platform() -> None:
    assert "detect_csv_platform" not in shelfshift.__all__
    assert "detect_csv_platform" not in shelfshift._LAZY_EXPORTS
    try:
        _ = shelfshift.detect_csv_platform
    except AttributeError:
        pass
    else:
        raise AssertionError("shelfshift.detect_csv_platform should not be exported")


def test_facade_does_not_export_app() -> None:
    assert "app" not in shelfshift.__all__
    assert "app" not in shelfshift._LAZY_EXPORTS
    try:
        _ = shelfshift.app
    except AttributeError:
        pass
    else:
        raise AssertionError("shelfshift.app should not be exported")


def test_facade_does_not_export_create_app() -> None:
    assert "create_app" not in shelfshift.__all__
    assert "create_app" not in shelfshift._LAZY_EXPORTS
    try:
        _ = shelfshift.create_app
    except AttributeError:
        pass
    else:
        raise AssertionError("shelfshift.create_app should not be exported")


def test_facade_does_not_export_export_csv_for_target() -> None:
    assert "export_csv_for_target" not in shelfshift.__all__
    assert "export_csv_for_target" not in shelfshift._LAZY_EXPORTS
    try:
        _ = shelfshift.export_csv_for_target
    except AttributeError:
        pass
    else:
        raise AssertionError("shelfshift.export_csv_for_target should not be exported")


def test_facade_does_not_export_product_type() -> None:
    assert "Product" not in shelfshift.__all__
    assert "Product" not in shelfshift._LAZY_EXPORTS
    try:
        _ = shelfshift.Product
    except AttributeError:
        pass
    else:
        raise AssertionError("shelfshift.Product should not be exported")


def test_facade_does_not_export_parse_product_payload() -> None:
    assert "parse_product_payload" not in shelfshift.__all__
    assert "parse_product_payload" not in shelfshift._LAZY_EXPORTS
    try:
        _ = shelfshift.parse_product_payload
    except AttributeError:
        pass
    else:
        raise AssertionError("shelfshift.parse_product_payload should not be exported")
