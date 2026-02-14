import json
from pathlib import Path

import requests

from app.services.importer.platforms.shopify import ShopifyClient
from app.services.importer.platforms.squarespace import SquarespaceClient
from app.services.importer.platforms.woocommerce import WooCommerceClient

_FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "importers"


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
    assert product.to_dict(include_raw=False) == expected


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
    assert product.to_dict(include_raw=False) == expected


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
    assert product.to_dict(include_raw=False) == expected


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
    assert product.to_dict(include_raw=False) == expected


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
    assert product.to_dict(include_raw=False) == expected


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
    assert product.to_dict(include_raw=False) == expected
