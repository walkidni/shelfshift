import json
from pathlib import Path

import pytest
import requests

from app.models import normalize_currency, parse_decimal_money
from app.services.importer.platforms import (
    AliExpressClient,
    AmazonRapidApiClient,
    ApiConfig,
    ShopifyClient,
    SquarespaceClient,
    WooCommerceClient,
)

_TMP_INPUT_ROOT = Path(__file__).resolve().parent.parent / "tmp" / "importer-raw-payloads"
_REQUIRED_INPUTS = ("shopify", "squarespace", "woocommerce", "amazon", "aliexpress")
_MISSING_INPUTS = [name for name in _REQUIRED_INPUTS if not (_TMP_INPUT_ROOT / f"{name}.json").exists()]
pytestmark = pytest.mark.skipif(
    bool(_MISSING_INPUTS),
    reason=f"Missing tmp importer input payloads: {', '.join(_MISSING_INPUTS)}",
)


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self):
        return self._payload


def _load_input_payload(name: str) -> dict:
    path = _TMP_INPUT_ROOT / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_product_dual_write(product, *, source_url: str) -> None:
    assert product.source is not None
    assert product.source.platform
    assert product.source.url == source_url

    assert product.price is not None
    assert product.price.current.currency is None or product.price.current.currency == normalize_currency(
        product.price.current.currency
    )

    assert product.options is not None
    for option in product.options:
        assert option.name
        assert isinstance(option.values, list)

    if product.source.id:
        assert product.identifiers is not None
        assert product.identifiers.values.get("source_product_id") == product.source.id

    assert product.variants
    for variant in product.variants:
        assert variant.price is not None
        assert variant.price.current.currency is None or variant.price.current.currency == normalize_currency(
            variant.price.current.currency
        )

        assert variant.option_values is not None
        for option_value in variant.option_values:
            assert option_value.name
            assert option_value.value

        assert variant.inventory is not None

        if variant.id:
            assert variant.identifiers is not None
            assert variant.identifiers.values.get("source_variant_id") == variant.id


def test_shopify_import_populates_phase4_typed_fields(monkeypatch) -> None:
    payload_input = _load_input_payload("shopify")
    source_url = payload_input["url"]
    api_payload = payload_input["raw"]
    client = ShopifyClient()

    expected_api_url = "https://hears.com/products/jet-black.json"

    def fake_get(url: str, params=None, timeout=None, headers=None):
        assert timeout == client._http.request_timeout
        assert params is None
        assert headers is None
        assert url == expected_api_url
        return _FakeResponse(payload=api_payload)

    monkeypatch.setattr(client._http, "get", fake_get)
    product = client.fetch_product(source_url)

    _assert_product_dual_write(product, source_url=source_url)
    assert product.media
    assert product.media[0].alt == "Hears Earplug black"
    assert product.media[0].position == 1
    assert product.variants[0].identifiers is not None
    assert product.variants[0].identifiers.values.get("barcode") == "8721082842037"


def test_squarespace_import_populates_phase4_typed_fields(monkeypatch) -> None:
    payload_input = _load_input_payload("squarespace")
    source_url = payload_input["url"]
    page_json_payload = payload_input["raw"]
    client = SquarespaceClient()

    expected_page_json_url = f"{source_url}?format=json"

    def fake_get(url: str, params=None, timeout=None, headers=None):
        assert timeout == client._http.request_timeout
        assert params is None
        assert headers is None
        assert url == expected_page_json_url
        return _FakeResponse(payload=page_json_payload)

    monkeypatch.setattr(client._http, "get", fake_get)
    product = client.fetch_product(source_url)

    _assert_product_dual_write(product, source_url=source_url)
    assert product.media
    assert product.media[0].alt == "IMG_5114.jpeg"
    assert product.media[0].position == 1
    assert product.variants[0].inventory is not None
    assert product.variants[0].inventory.track_quantity is True


def test_woocommerce_import_populates_phase4_typed_fields(monkeypatch) -> None:
    payload_input = _load_input_payload("woocommerce")
    source_url = payload_input["url"]
    api_payload = payload_input["raw"]
    client = WooCommerceClient()

    expected_api_url = "https://za.sunglasshut.com/wp-json/wc/store/v1/products"

    def fake_get(url: str, params=None, timeout=None, headers=None):
        assert timeout == client._http.request_timeout
        assert headers is None
        if url == expected_api_url:
            assert params == {"slug": "oo9488-flak-2-0-xxl-888392682499"}
            return _FakeResponse(payload=api_payload)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(client._http, "get", fake_get)
    product = client.fetch_product(source_url)

    _assert_product_dual_write(product, source_url=source_url)
    assert product.identifiers is not None
    assert product.identifiers.values.get("sku") == "888392682499"
    assert product.variants[0].inventory is not None
    assert product.variants[0].inventory.allow_backorder is False


def test_amazon_import_populates_phase4_typed_fields(monkeypatch) -> None:
    payload_input = _load_input_payload("amazon")
    source_url = payload_input["url"]
    api_payload = payload_input["raw"]
    client = AmazonRapidApiClient(ApiConfig(rapidapi_key="test-key"))

    expected_api_url = "https://real-time-amazon-data.p.rapidapi.com/product-details"

    def fake_get(url: str, params=None, timeout=None, headers=None):
        assert timeout == client._http.request_timeout
        assert url == expected_api_url
        assert params == {"asin": "B0DZZWMB2L", "country": "US"}
        assert headers is not None
        return _FakeResponse(payload=api_payload)

    monkeypatch.setattr(client._http, "get", fake_get)
    product = client.fetch_product(source_url)

    _assert_product_dual_write(product, source_url=source_url)
    assert product.price is not None
    assert product.price.compare_at is not None
    assert product.price.compare_at.amount == parse_decimal_money("$1,499.99")
    assert product.taxonomy is not None
    assert product.taxonomy.paths
    assert product.taxonomy.paths[0] == [
        "Electronics",
        "Computers & Accessories",
        "Computers & Tablets",
        "Laptops",
        "Traditional Laptops",
    ]
    assert product.identifiers is not None
    assert product.identifiers.values.get("parent_asin") == "B0FDCYVV8X"


def test_aliexpress_import_populates_phase4_typed_fields(monkeypatch) -> None:
    payload_input = _load_input_payload("aliexpress")
    source_url = payload_input["url"]
    api_payload = payload_input["raw"]
    client = AliExpressClient(ApiConfig(rapidapi_key="test-key"))

    expected_api_url = "https://aliexpress-datahub.p.rapidapi.com/item_detail_6"

    def fake_get(url: str, params=None, timeout=None, headers=None):
        assert timeout == client._http.request_timeout
        assert url == expected_api_url
        assert params == {"itemId": "1005008518647948"}
        assert headers is not None
        return _FakeResponse(payload=api_payload)

    monkeypatch.setattr(client._http, "get", fake_get)
    product = client.fetch_product(source_url)

    _assert_product_dual_write(product, source_url=source_url)
    assert any(media.type == "video" and "video.aliexpress-media.com" in media.url for media in product.media)
    assert product.variants[0].price is not None
    assert product.variants[0].price.compare_at is not None
    assert product.variants[0].price.compare_at.amount == parse_decimal_money("120.00")
