import requests

from app.services.platforms.woocommerce import WooCommerceClient


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


def test_woocommerce_storefront_url_uses_store_api_slug_and_parses_product(monkeypatch) -> None:
    client = WooCommerceClient()
    api_payload = [
        {
            "id": 101,
            "name": "Adjustable Wrench Set",
            "slug": "adjustable-wrench-set",
            "description": "<p>Heavy duty set</p>",
            "prices": {
                "currency_code": "USD",
                "currency_minor_unit": 2,
                "price": "2900",
            },
            "images": [{"src": "https://demo-store.com/wp-content/uploads/wrench.jpg"}],
            "is_in_stock": True,
            "attributes": [{"name": "Material", "terms": [{"name": "Steel"}]}],
        }
    ]

    calls: list[tuple[str, dict | None]] = []

    def fake_get(url: str, params=None, timeout=None, headers=None):
        calls.append((url, params))
        assert timeout == client._http.request_timeout
        assert headers is None
        if url == "https://demo-store.com/wp-json/wc/store/v1/products":
            assert params == {"slug": "adjustable-wrench-set"}
            return _FakeResponse(payload=api_payload)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product("https://demo-store.com/product/adjustable-wrench-set/")

    assert calls == [("https://demo-store.com/wp-json/wc/store/v1/products", {"slug": "adjustable-wrench-set"})]
    assert product.platform == "woocommerce"
    assert product.id == "101"
    assert product.slug == "adjustable-wrench-set"
    assert product.title == "Adjustable Wrench Set"
    assert product.price == {"amount": 29.0, "currency": "USD"}
    assert product.images == ["https://demo-store.com/wp-content/uploads/wrench.jpg"]
    assert product.options == {"Material": ["Steel"]}
    assert len(product.variants) == 1
    assert product.variants[0].id == "101"
    assert product.raw == api_payload


def test_woocommerce_store_api_url_imports_directly_without_normalizing(monkeypatch) -> None:
    client = WooCommerceClient()
    api_url = "https://demo-store.com/wp-json/wc/store/v1/products/321"
    api_payload = {
        "id": 321,
        "name": "Brake Disc Rotor",
        "slug": "brake-disc-rotor",
        "description": "<p>Solid rotor.</p>",
        "prices": {
            "currency_code": "USD",
            "currency_minor_unit": 2,
            "price": "7999",
        },
        "images": [{"src": "https://demo-store.com/wp-content/uploads/rotor.jpg"}],
        "is_in_stock": True,
        "variations": [
            {
                "id": 501,
                "name": "Rotor / 300mm",
                "attributes": [{"name": "Size", "option": "300mm"}],
                "prices": {"currency_code": "USD", "currency_minor_unit": 2, "price": "7999"},
                "stock_quantity": 7,
            },
            {},
        ],
    }

    calls: list[str] = []

    def fake_get(url: str, params=None, timeout=None, headers=None):
        calls.append(url)
        assert timeout == client._http.request_timeout
        assert headers is None
        assert params is None
        assert url == api_url
        return _FakeResponse(payload=api_payload)

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product(api_url)

    assert calls == [api_url]
    assert product.platform == "woocommerce"
    assert product.id == "321"
    assert product.slug == "brake-disc-rotor"
    assert len(product.variants) == 1
    assert product.variants[0].id == "501"
    assert product.variants[0].options == {"Size": "300mm"}
    assert product.variants[0].inventory_quantity == 7
    assert product.raw == api_payload


def test_woocommerce_import_falls_back_to_default_variant_for_broken_variations(monkeypatch) -> None:
    client = WooCommerceClient()
    api_payload = {
        "id": 778,
        "name": "Spare Part",
        "slug": "spare-part",
        "description": "<p>Simple spare part.</p>",
        "images": [],
        "variations": [{}],
    }

    def fake_get(url: str, params=None, timeout=None, headers=None):
        assert url == "https://demo-store.com/wp-json/wc/store/v1/products/778"
        return _FakeResponse(payload=api_payload)

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product("https://demo-store.com/wp-json/wc/store/v1/products/778")

    assert len(product.variants) == 1
    assert product.variants[0].id == "778"
    assert product.variants[0].sku is None


def test_woocommerce_store_api_failure_uses_heuristic_html_fallback(monkeypatch) -> None:
    client = WooCommerceClient()
    api_url = "https://demo-store.com/wp-json/wc/store/v1/products/brake-disc-rotor"
    fallback_url = "https://demo-store.com/product/brake-disc-rotor/"
    html = """
    <html><head>
      <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Product",
          "name": "Brake Disc Rotor",
          "description": "Fallback product",
          "offers": {
            "@type": "Offer",
            "price": "19.99",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock"
          }
        }
      </script>
    </head></html>
    """

    calls: list[str] = []

    def fake_get(url: str, params=None, timeout=None, headers=None):
        calls.append(url)
        if url == api_url:
            return _FakeResponse(status_code=503, text="Store API unavailable")
        if url == fallback_url:
            assert isinstance(headers, dict)
            return _FakeResponse(text=html)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product(api_url)

    assert calls == [api_url, fallback_url]
    assert product.title == "Brake Disc Rotor"
    assert product.price == {"amount": 19.99, "currency": "USD"}
    assert len(product.variants) == 1


def test_woocommerce_import_raises_value_error_when_api_and_fallback_fail(monkeypatch) -> None:
    client = WooCommerceClient()
    api_url = "https://demo-store.com/wp-json/wc/store/v1/products/empty-product"
    fallback_url = "https://demo-store.com/product/empty-product/"

    def fake_get(url: str, params=None, timeout=None, headers=None):
        if url == api_url:
            return _FakeResponse(payload=[])
        if url == fallback_url:
            return _FakeResponse(text="<html><body>No product metadata</body></html>")
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(client._http, "get", fake_get)

    try:
        client.fetch_product(api_url)
    except ValueError as exc:
        assert "WooCommerce import failed" in str(exc)
    else:
        raise AssertionError("Expected ValueError for failed API and failed fallback.")
