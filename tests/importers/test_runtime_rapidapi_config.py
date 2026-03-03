from __future__ import annotations

import pytest

from shelfshift.core import api as core_api
from shelfshift.core.importers import url as url_importers

_AMAZON_URL = "https://www.amazon.com/dp/B0C1234567"
_ALIEXPRESS_URL = "https://www.aliexpress.com/item/1005008518647948.html"


def test_import_product_from_url_rejects_detectable_but_unsupported_platforms() -> None:
    with pytest.raises(ValueError, match="Unsupported URL import source"):
        url_importers.import_product_from_url(_AMAZON_URL)

    with pytest.raises(ValueError, match="Unsupported URL import source"):
        url_importers.import_product_from_url(_ALIEXPRESS_URL)


def test_import_products_from_urls_collects_unsupported_platform_errors(monkeypatch) -> None:
    class _FakeProduct:
        pass

    monkeypatch.setattr(url_importers, "_fetch_product_details", lambda _url: _FakeProduct())

    products, errors = url_importers.import_products_from_urls(
        [
            "https://demo.myshopify.com/products/red-rain-coat",
            _AMAZON_URL,
            _ALIEXPRESS_URL,
        ]
    )

    assert len(products) == 1
    assert len(errors) == 2
    assert {error["url"] for error in errors} == {_AMAZON_URL, _ALIEXPRESS_URL}
    assert all("Unsupported URL import source" in error["detail"] for error in errors)


def test_core_import_url_strict_raises_for_unsupported_platforms() -> None:
    with pytest.raises(ValueError, match="Strict mode failed with 1 URL import error"):
        core_api.import_url([_AMAZON_URL], strict=True)
