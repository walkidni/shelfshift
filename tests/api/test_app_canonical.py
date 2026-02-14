from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models import Money, Price, Product, SourceRef

from tests.helpers._app_helpers import patch_run_import_product


client = TestClient(app)


def test_import_endpoint_returns_canonical_payload(monkeypatch) -> None:
    product = Product(
        source=SourceRef(platform="shopify", id="123", slug="demo-mug", url="https://store.example/products/demo-mug"),
        title="Demo Mug",
        description="Demo description",
        price=Price(current=Money(amount=Decimal("12.0"), currency="USD")),
    )
    patch_run_import_product(
        monkeypatch,
        expected_url="https://example.myshopify.com/products/demo-mug",
        product=product,
    )

    response = client.post(
        "/api/v1/import",
        json={"product_url": "https://example.myshopify.com/products/demo-mug"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == {
        "platform": "shopify",
        "id": "123",
        "slug": "demo-mug",
        "url": "https://store.example/products/demo-mug",
    }
    assert payload["price"] == {
        "current": {"amount": "12", "currency": "USD"},
        "compare_at": None,
        "cost": None,
        "min_price": None,
        "max_price": None,
    }
    assert payload.get("raw") is None
