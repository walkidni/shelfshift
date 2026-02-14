import json
from pathlib import Path

import requests
from app.models import format_decimal, normalize_currency, parse_decimal_money

from app.services.importer.platforms.shopify import ShopifyClient
from app.services.importer.platforms.squarespace import SquarespaceClient
from app.services.importer.platforms.woocommerce import WooCommerceClient

_FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "importers"


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


def _load_json(relative_path: str) -> dict:
    path = _FIXTURES_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def _load_text(relative_path: str) -> str:
    path = _FIXTURES_ROOT / relative_path
    return path.read_text(encoding="utf-8")


def _amount_text(value) -> str | None:
    parsed = parse_decimal_money(value)
    if parsed is None:
        return None
    return format_decimal(parsed)


def _assert_matches_legacy_fixture_shape(parsed: dict, expected: dict) -> None:
    assert parsed["source"]["platform"] == expected.get("platform")
    assert parsed["source"]["id"] == expected.get("id")
    assert parsed["source"]["slug"] == expected.get("slug")
    assert parsed["title"] == expected.get("title")
    assert parsed["description"] == expected.get("description")
    assert parsed["brand"] == expected.get("brand")
    assert parsed["vendor"] == expected.get("vendor")
    assert parsed["tags"] == expected.get("tags", [])
    assert parsed["requires_shipping"] is expected.get("requires_shipping")
    assert parsed["track_quantity"] is expected.get("track_quantity")
    assert parsed["is_digital"] is expected.get("is_digital")

    expected_options = expected.get("options") or {}
    parsed_options = {option["name"]: option["values"] for option in parsed["options"]}
    assert parsed_options == expected_options

    expected_price = expected.get("price") or {}
    assert parsed["price"]["current"]["amount"] == _amount_text(expected_price.get("amount"))
    assert parsed["price"]["current"]["currency"] == normalize_currency(expected_price.get("currency"))

    expected_category = expected.get("category")
    if expected_category:
        assert parsed["taxonomy"]["paths"]
        assert parsed["taxonomy"]["paths"][0][-1] == expected_category

    expected_images = expected.get("images") or []
    parsed_images = [item["url"] for item in parsed["media"] if item["type"] == "image"]
    if expected_images:
        assert expected_images[0] in parsed_images

    expected_variants = expected.get("variants") or []
    assert len(parsed["variants"]) == len(expected_variants)
    for parsed_variant, expected_variant in zip(parsed["variants"], expected_variants):
        assert parsed_variant["id"] == expected_variant.get("id")
        assert parsed_variant["sku"] == expected_variant.get("sku")
        assert parsed_variant["title"] == expected_variant.get("title")
        assert parsed_variant["price"]["current"]["amount"] == _amount_text(expected_variant.get("price_amount"))
        assert parsed_variant["price"]["current"]["currency"] == normalize_currency(expected_variant.get("currency"))
        assert parsed_variant["inventory"]["quantity"] == expected_variant.get("inventory_quantity")
        assert parsed_variant["inventory"]["available"] is expected_variant.get("available")
        assert {item["name"]: item["value"] for item in parsed_variant["option_values"]} == (
            expected_variant.get("options") or {}
        )


def test_shopify_import_happy_path_matches_expected_fixture(monkeypatch) -> None:
    client = ShopifyClient()
    source_url = "https://demo-shop.myshopify.com/products/classic-tee"
    api_url = "https://demo-shop.myshopify.com/products/classic-tee.json"
    payload = _load_json("shopify/product_api.json")
    expected = _load_json("shopify/product_api.expected.json")

    calls: list[str] = []

    def fake_get(url: str, params=None, timeout=None, headers=None):
        calls.append(url)
        assert timeout == client._http.request_timeout
        assert params is None
        assert headers is None
        assert url == api_url
        return _FakeResponse(payload=payload)

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product(source_url)

    assert calls == [api_url]
    _assert_matches_legacy_fixture_shape(product.to_dict(include_raw=False), expected)


def test_shopify_import_html_fallback_matches_expected_fixture(monkeypatch) -> None:
    client = ShopifyClient()
    source_url = "https://demo-shop.myshopify.com/products/fallback-mug"
    api_url = "https://demo-shop.myshopify.com/products/fallback-mug.json"
    html = _load_text("shopify/product_jsonld.html")
    expected = _load_json("shopify/product_jsonld.expected.json")

    calls: list[str] = []

    def fake_get(url: str, params=None, timeout=None, headers=None):
        calls.append(url)
        assert timeout == client._http.request_timeout
        assert params is None
        if url == api_url:
            assert headers is None
            return _FakeResponse(status_code=404)
        if url == source_url:
            assert isinstance(headers, dict)
            return _FakeResponse(text=html)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product(source_url)

    assert calls == [api_url, source_url]
    _assert_matches_legacy_fixture_shape(product.to_dict(include_raw=False), expected)


def test_squarespace_import_happy_path_matches_expected_fixture(monkeypatch) -> None:
    client = SquarespaceClient()
    source_url = "https://st-p-sews.squarespace.com/shop/p/custom-patchwork-shirt-snzgy"
    page_json_url = f"{source_url}?format=json"
    payload = _load_json("squarespace/product_page_json.json")
    expected = _load_json("squarespace/product_page_json.expected.json")

    calls: list[str] = []

    def fake_get(url: str, params=None, timeout=None, headers=None):
        calls.append(url)
        assert timeout == client._http.request_timeout
        assert params is None
        assert headers is None
        assert url == page_json_url
        return _FakeResponse(payload=payload)

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product(source_url)

    assert calls == [page_json_url]
    _assert_matches_legacy_fixture_shape(product.to_dict(include_raw=False), expected)


def test_squarespace_import_html_fallback_matches_expected_fixture(monkeypatch) -> None:
    client = SquarespaceClient()
    source_url = "https://st-p-sews.squarespace.com/shop/p/custom-patchwork-shirt-snzgy"
    page_json_url = f"{source_url}?format=json"
    non_product_payload = _load_json("squarespace/non_product_page_json.json")
    html = _load_text("squarespace/product_jsonld.html")
    expected = _load_json("squarespace/product_jsonld.expected.json")

    calls: list[str] = []

    def fake_get(url: str, params=None, timeout=None, headers=None):
        calls.append(url)
        assert timeout == client._http.request_timeout
        assert params is None
        if url == page_json_url:
            assert headers is None
            return _FakeResponse(payload=non_product_payload)
        if url == source_url:
            assert isinstance(headers, dict)
            return _FakeResponse(text=html)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product(source_url)

    assert calls == [page_json_url, source_url]
    _assert_matches_legacy_fixture_shape(product.to_dict(include_raw=False), expected)


def test_woocommerce_import_happy_path_matches_expected_fixture(monkeypatch) -> None:
    client = WooCommerceClient()
    source_url = "https://demo-store.com/product/adjustable-wrench-set/"
    api_url = "https://demo-store.com/wp-json/wc/store/v1/products"
    payload = _load_json("woocommerce/store_api_slug_response.json")
    expected = _load_json("woocommerce/store_api_slug.expected.json")

    calls: list[tuple[str, dict | None]] = []

    def fake_get(url: str, params=None, timeout=None, headers=None):
        calls.append((url, params))
        assert timeout == client._http.request_timeout
        assert headers is None
        if url == api_url:
            assert params == {"slug": "adjustable-wrench-set"}
            return _FakeResponse(payload=payload)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product(source_url)

    assert calls == [(api_url, {"slug": "adjustable-wrench-set"})]
    _assert_matches_legacy_fixture_shape(product.to_dict(include_raw=False), expected)


def test_woocommerce_import_html_fallback_matches_expected_fixture(monkeypatch) -> None:
    client = WooCommerceClient()
    api_url = "https://demo-store.com/wp-json/wc/store/v1/products/brake-disc-rotor"
    fallback_url = "https://demo-store.com/product/brake-disc-rotor/"
    error_text = _load_text("woocommerce/store_api_error_body.txt")
    html = _load_text("woocommerce/product_jsonld.html")
    expected = _load_json("woocommerce/product_jsonld.expected.json")

    calls: list[str] = []

    def fake_get(url: str, params=None, timeout=None, headers=None):
        calls.append(url)
        assert timeout == client._http.request_timeout
        assert params is None
        if url == api_url:
            assert headers is None
            return _FakeResponse(status_code=503, text=error_text)
        if url == fallback_url:
            assert isinstance(headers, dict)
            return _FakeResponse(text=html)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product(api_url)

    assert calls == [api_url, fallback_url]
    _assert_matches_legacy_fixture_shape(product.to_dict(include_raw=False), expected)
