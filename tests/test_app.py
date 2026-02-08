from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_detect_rejects_unknown_platform() -> None:
    response = client.get("/api/v1/detect", params={"url": "https://example.com/anything"})
    assert response.status_code == 200
    assert response.json()["platform"] is None


def test_import_endpoint_uses_service(monkeypatch) -> None:
    def fake_run_import(product_url: str) -> dict:
        assert product_url == "https://demo.myshopify.com/products/mug"
        return {
            "platform": "shopify",
            "id": "123",
            "title": "Demo Mug",
            "description": "Demo description",
            "price": {"amount": 12.0, "currency": "USD"},
            "images": [],
            "options": {},
            "variants": [],
            "brand": None,
            "category": None,
            "meta_title": None,
            "meta_description": None,
            "slug": None,
            "tags": [],
            "vendor": None,
            "weight": None,
            "requires_shipping": True,
            "track_quantity": True,
            "is_digital": False,
            "raw": {},
        }

    monkeypatch.setattr("app.main._run_import", fake_run_import)

    response = client.post(
        "/api/v1/import",
        json={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert response.json()["platform"] == "shopify"
    assert response.json()["title"] == "Demo Mug"


def test_home_page_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "TradeMint" in response.text
