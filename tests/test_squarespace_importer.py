import requests

from app.services.importer.platforms.squarespace import SquarespaceClient


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


def test_squarespace_import_prefers_page_json_when_product_structured_content_exists(monkeypatch) -> None:
    client = SquarespaceClient()
    source_url = "https://st-p-sews.squarespace.com/shop/p/custom-patchwork-shirt-snzgy"
    page_json_url = f"{source_url}?format=json"

    payload = {
        "item": {
            "id": "abc123",
            "recordTypeLabel": "product",
            "title": "Custom Patchwork Shirt",
            "urlId": "custom-patchwork-shirt-snzgy",
            "assetUrl": "https://images.example.com/front.jpg",
            "tags": ["patchwork", "shirt"],
            "categories": ["Tops"],
            "structuredContent": {
                "description": "<p>Handmade shirt.</p>",
                "productType": "PHYSICAL",
                "variantOptions": [
                    {"name": "Color", "values": [{"value": "Blue"}, {"value": "Red"}]},
                    {"name": "Size", "values": [{"value": "S"}, {"value": "M"}]},
                ],
                "variants": [
                    {
                        "id": "v1",
                        "sku": "SQ-001",
                        "optionValues": ["Blue", "S"],
                        "priceMoney": {"value": "120.00", "currency": "USD"},
                        "inStock": True,
                        "stock": 4,
                        "image": {"assetUrl": "https://images.example.com/blue-s.jpg"},
                    },
                    {
                        "id": "v2",
                        "sku": "SQ-002",
                        "optionValues": ["Red", "M"],
                        "priceMoney": {"value": "130.00", "currency": "USD"},
                        "inStock": False,
                        "stock": 0,
                    },
                ],
            },
        }
    }

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
    assert product.platform == "squarespace"
    assert product.id == "abc123"
    assert product.slug == "custom-patchwork-shirt-snzgy"
    assert product.title == "Custom Patchwork Shirt"
    assert product.price == {"amount": 120.0, "currency": "USD"}
    assert product.images == [
        "https://images.example.com/front.jpg",
        "https://images.example.com/blue-s.jpg",
    ]
    assert product.options == {"Color": ["Blue", "Red"], "Size": ["S", "M"]}
    assert product.tags == ["patchwork", "shirt"]
    assert product.category == "Tops"
    assert len(product.variants) == 2
    assert product.variants[0].id == "v1"
    assert product.variants[0].options == {"Color": "Blue", "Size": "S"}
    assert product.variants[0].price_amount == 120.0
    assert product.variants[0].inventory_quantity == 4
    assert product.variants[1].id == "v2"
    assert product.variants[1].options == {"Color": "Red", "Size": "M"}
    assert product.variants[1].price_amount == 130.0
    assert product.variants[1].available is False


def test_squarespace_import_falls_back_to_html_json_ld_when_page_json_has_no_product(monkeypatch) -> None:
    client = SquarespaceClient()
    source_url = "https://st-p-sews.squarespace.com/shop/p/custom-patchwork-shirt-snzgy"
    page_json_url = f"{source_url}?format=json"

    html = """
    <html><head>
      <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Product",
          "name": "Custom Patchwork Shirt",
          "description": "Handmade shirt",
          "image": ["https://images.example.com/front.jpg"],
          "brand": {"@type": "Brand", "name": "ST-P SEWS"},
          "offers": [
            {
              "@type": "Offer",
              "sku": "SQ-001",
              "name": "Blue / S",
              "price": "120.00",
              "priceCurrency": "USD",
              "availability": "https://schema.org/InStock"
            },
            {
              "@type": "Offer",
              "sku": "SQ-002",
              "name": "Red / M",
              "price": "130.00",
              "priceCurrency": "USD",
              "availability": "https://schema.org/OutOfStock"
            }
          ]
        }
      </script>
    </head></html>
    """

    calls: list[str] = []

    def fake_get(url: str, params=None, timeout=None, headers=None):
        calls.append(url)
        assert timeout == client._http.request_timeout
        assert params is None
        if url == page_json_url:
            assert headers is None
            return _FakeResponse(payload={"collection": {"title": "Shop"}})
        if url == source_url:
            assert isinstance(headers, dict)
            return _FakeResponse(text=html)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(client._http, "get", fake_get)

    product = client.fetch_product(source_url)

    assert calls == [page_json_url, source_url]
    assert product.platform == "squarespace"
    assert product.slug == "custom-patchwork-shirt-snzgy"
    assert product.title == "Custom Patchwork Shirt"
    assert product.brand == "ST-P SEWS"
    assert product.price == {"amount": 120.0, "currency": "USD"}
    assert len(product.variants) == 2
    assert product.variants[0].sku == "SQ-001"
    assert product.variants[0].options == {"Option": "Blue / S"}
    assert product.variants[1].sku == "SQ-002"
    assert product.variants[1].available is False


def test_squarespace_import_rejects_non_product_url() -> None:
    client = SquarespaceClient()

    try:
        client.fetch_product("https://st-p-sews.squarespace.com/")
    except ValueError as exc:
        assert "not a product URL" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-product Squarespace URL.")
