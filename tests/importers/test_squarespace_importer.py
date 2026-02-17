import requests

from shelfshift.core.importers.url.platforms.squarespace import SquarespaceClient


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
    parsed = product.to_dict(include_raw=False)

    assert calls == [page_json_url]
    assert parsed["source"]["platform"] == "squarespace"
    assert parsed["source"]["id"] == "abc123"
    assert parsed["source"]["slug"] == "custom-patchwork-shirt-snzgy"
    assert parsed["title"] == "Custom Patchwork Shirt"
    assert parsed["price"]["current"] == {"amount": "120", "currency": "USD"}
    assert [item["url"] for item in parsed["media"] if item["type"] == "image"] == [
        "https://images.example.com/front.jpg",
    ]
    assert parsed["options"] == [
        {"name": "Color", "values": ["Blue", "Red"]},
        {"name": "Size", "values": ["S", "M"]},
    ]
    assert parsed["tags"] == ["patchwork", "shirt"]
    assert parsed["taxonomy"]["primary"] == ["Tops"]
    assert len(parsed["variants"]) == 2
    assert parsed["variants"][0]["id"] == "v1"
    assert parsed["variants"][0]["option_values"] == [{"name": "Color", "value": "Blue"}, {"name": "Size", "value": "S"}]
    assert parsed["variants"][0]["price"]["current"] == {"amount": "120", "currency": "USD"}
    assert parsed["variants"][0]["inventory"]["quantity"] == 4
    assert parsed["variants"][1]["id"] == "v2"
    assert parsed["variants"][1]["option_values"] == [{"name": "Color", "value": "Red"}, {"name": "Size", "value": "M"}]
    assert parsed["variants"][1]["price"]["current"] == {"amount": "130", "currency": "USD"}
    assert parsed["variants"][1]["inventory"]["available"] is False


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
    parsed = product.to_dict(include_raw=False)

    assert calls == [page_json_url, source_url]
    assert parsed["source"]["platform"] == "squarespace"
    assert parsed["source"]["slug"] == "custom-patchwork-shirt-snzgy"
    assert parsed["title"] == "Custom Patchwork Shirt"
    assert parsed["brand"] == "ST-P SEWS"
    assert parsed["price"]["current"] == {"amount": "120", "currency": "USD"}
    assert len(parsed["variants"]) == 2
    assert parsed["variants"][0]["sku"] == "SQ-001"
    assert parsed["variants"][0]["option_values"] == [{"name": "Option", "value": "Blue / S"}]
    assert parsed["variants"][1]["sku"] == "SQ-002"
    assert parsed["variants"][1]["inventory"]["available"] is False


def test_squarespace_import_rejects_non_product_url() -> None:
    client = SquarespaceClient()

    try:
        client.fetch_product("https://st-p-sews.squarespace.com/")
    except ValueError as exc:
        assert "not a product URL" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-product Squarespace URL.")
