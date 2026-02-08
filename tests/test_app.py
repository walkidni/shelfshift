from fastapi.testclient import TestClient
import io

import pandas as pd

from app.main import app
from app.services.exporters.shopify_csv import SHOPIFY_COLUMNS
from app.services.exporters.woocommerce_csv import WOOCOMMERCE_COLUMNS
from app.services.importer import ProductResult, Variant


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
    def fake_run_import_product(product_url: str) -> ProductResult:
        assert product_url == "https://demo.myshopify.com/products/mug"
        return ProductResult(
            platform="shopify",
            id="123",
            title="Demo Mug",
            description="Demo description",
            price={"amount": 12.0, "currency": "USD"},
            images=[],
            options={},
            variants=[],
            brand=None,
            category=None,
            meta_title=None,
            meta_description=None,
            slug=None,
            tags=[],
            vendor=None,
            weight=None,
            requires_shipping=True,
            track_quantity=True,
            is_digital=False,
            raw={},
        )

    monkeypatch.setattr("app.main._run_import_product", fake_run_import_product)

    response = client.post(
        "/api/v1/import",
        json={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert response.json()["platform"] == "shopify"
    assert response.json()["title"] == "Demo Mug"


def test_export_shopify_csv_endpoint(monkeypatch) -> None:
    def fake_run_import_product(product_url: str) -> ProductResult:
        assert product_url == "https://demo.myshopify.com/products/mug"
        return ProductResult(
            platform="shopify",
            id="123",
            title="Demo Mug",
            description="Demo description",
            price={"amount": 12.0, "currency": "USD"},
            images=["https://cdn.example.com/mug-front.jpg"],
            options={"Color": ["Black"]},
            variants=[
                Variant(
                    id="var-1",
                    sku="MUG-001",
                    options={"Color": "Black"},
                    price_amount=12.0,
                    inventory_quantity=10,
                    weight=250,
                    image="https://cdn.example.com/mug-black.jpg",
                )
            ],
            brand="Demo",
            category="Mugs",
            meta_title=None,
            meta_description=None,
            slug="demo-mug",
            tags=["mug", "coffee"],
            vendor="Demo",
            weight=250,
            requires_shipping=True,
            track_quantity=True,
            is_digital=False,
            raw={},
        )

    monkeypatch.setattr("app.main._run_import_product", fake_run_import_product)

    response = client.get(
        "/api/v1/export/shopify.csv",
        params={"url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="demo-mug.csv"'
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Handle"] == "demo-mug"
    assert frame.loc[0, "Title"] == "Demo Mug"
    assert frame.loc[0, "Option1 Name"] == "Color"
    assert frame.loc[0, "Option1 Value"] == "Black"
    assert frame.loc[0, "Variant SKU"] == "MUG-001"
    assert frame.loc[0, "Variant Image"] == "https://cdn.example.com/mug-black.jpg"
    assert frame.loc[0, "Variant Inventory Qty"] == "10"
    assert frame.loc[0, "Image Src"] == "https://cdn.example.com/mug-front.jpg"


def test_export_woocommerce_csv_endpoint(monkeypatch) -> None:
    def fake_run_import_product(product_url: str) -> ProductResult:
        assert product_url == "https://demo.myshopify.com/products/mug"
        return ProductResult(
            platform="shopify",
            id="123",
            title="Demo Mug",
            description="Demo description",
            price={"amount": 12.0, "currency": "USD"},
            images=["https://cdn.example.com/mug-front.jpg"],
            options={"Color": ["Black"]},
            variants=[
                Variant(
                    id="var-1",
                    sku="MUG-001",
                    options={"Color": "Black"},
                    price_amount=12.0,
                    inventory_quantity=10,
                    weight=250,
                    image="https://cdn.example.com/mug-black.jpg",
                )
            ],
            brand="Demo",
            category="Mugs",
            meta_title=None,
            meta_description=None,
            slug="demo-mug",
            tags=["mug", "coffee"],
            vendor="Demo",
            weight=250,
            requires_shipping=True,
            track_quantity=True,
            is_digital=False,
            raw={},
        )

    monkeypatch.setattr("app.main._run_import_product", fake_run_import_product)

    response = client.get(
        "/api/v1/export/woocommerce.csv",
        params={"url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="demo-mug.csv"'
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Type"] == "simple"
    assert frame.loc[0, "SKU"] == "SH:123"
    assert frame.loc[0, "Name"] == "Demo Mug"
    assert frame.loc[0, "Attribute 1 name"] == "Color"
    assert frame.loc[0, "Attribute 1 value(s)"] == "Black"
    assert frame.loc[0, "Manage stock?"] == "1"
    assert frame.loc[0, "Stock"] == "10"
    assert frame.loc[0, "Images"] == "https://cdn.example.com/mug-front.jpg"


def test_home_page_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "TradeMint" in response.text


def test_import_page_shows_shopify_and_woocommerce_links(monkeypatch) -> None:
    def fake_run_import_product(product_url: str) -> ProductResult:
        assert product_url == "https://demo.myshopify.com/products/mug"
        return ProductResult(
            platform="shopify",
            id="123",
            title="Demo Mug",
            description="Demo description",
            price={"amount": 12.0, "currency": "USD"},
            images=["https://cdn.example.com/mug-front.jpg"],
            options={},
            variants=[Variant(id="var-1", price_amount=12.0)],
            slug="demo-mug",
            raw={},
        )

    monkeypatch.setattr("app.main._run_import_product", fake_run_import_product)

    response = client.post(
        "/import",
        data={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert "Download Shopify CSV" in response.text
    assert "Download WooCommerce CSV" in response.text
    assert "/api/v1/export/shopify.csv?url=" in response.text
    assert "/api/v1/export/woocommerce.csv?url=" in response.text
