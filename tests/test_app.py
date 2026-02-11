from fastapi.testclient import TestClient
import io

import pandas as pd

from app.main import app
from app.services.exporters.shopify_csv import SHOPIFY_COLUMNS
from app.services.exporters.squarespace_csv import SQUARESPACE_COLUMNS
from app.services.exporters.wix_csv import WIX_COLUMNS
from app.services.exporters.woocommerce_csv import WOOCOMMERCE_COLUMNS
from app.services.importer import ProductResult, Variant
from tests._app_helpers import patch_run_import_product


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


def test_detect_woocommerce_product_url() -> None:
    response = client.get(
        "/api/v1/detect",
        params={"url": "https://producttable.barn2.com/product/adjustable-wrench-set/"},
    )
    assert response.status_code == 200
    assert response.json()["platform"] == "woocommerce"
    assert response.json()["is_product"] is True
    assert response.json()["slug"] == "adjustable-wrench-set"


def test_detect_squarespace_product_url() -> None:
    response = client.get(
        "/api/v1/detect",
        params={"url": "https://st-p-sews.squarespace.com/shop/p/custom-patchwork-shirt-snzgy"},
    )
    assert response.status_code == 200
    assert response.json()["platform"] == "squarespace"
    assert response.json()["is_product"] is True
    assert response.json()["slug"] == "custom-patchwork-shirt-snzgy"


def test_import_endpoint_uses_service(monkeypatch) -> None:
    product = ProductResult(
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
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    response = client.post(
        "/api/v1/import",
        json={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert response.json()["platform"] == "shopify"
    assert response.json()["title"] == "Demo Mug"


def test_import_endpoint_accepts_woocommerce_url(monkeypatch) -> None:
    product = ProductResult(
        platform="woocommerce",
        id="123",
        title="Adjustable Wrench Set",
        description="Demo description",
        price={"amount": 29.0, "currency": "USD"},
        images=[],
        options={},
        variants=[],
        brand=None,
        category=None,
        meta_title=None,
        meta_description=None,
        slug="adjustable-wrench-set",
        tags=[],
        vendor=None,
        weight=None,
        requires_shipping=True,
        track_quantity=True,
        is_digital=False,
        raw={},
    )
    patch_run_import_product(
        monkeypatch,
        expected_url="https://producttable.barn2.com/product/adjustable-wrench-set/",
        product=product,
    )

    response = client.post(
        "/api/v1/import",
        json={"product_url": "https://producttable.barn2.com/product/adjustable-wrench-set/"},
    )

    assert response.status_code == 200
    assert response.json()["platform"] == "woocommerce"
    assert response.json()["title"] == "Adjustable Wrench Set"


def test_import_endpoint_accepts_squarespace_url(monkeypatch) -> None:
    product = ProductResult(
        platform="squarespace",
        id="abc123",
        title="Custom Patchwork Shirt",
        description="Demo description",
        price={"amount": 120.0, "currency": "USD"},
        images=[],
        options={},
        variants=[],
        brand="ST-P SEWS",
        category="Shirts",
        meta_title=None,
        meta_description=None,
        slug="custom-patchwork-shirt-snzgy",
        tags=[],
        vendor="ST-P SEWS",
        weight=None,
        requires_shipping=True,
        track_quantity=True,
        is_digital=False,
        raw={},
    )
    patch_run_import_product(
        monkeypatch,
        expected_url="https://st-p-sews.squarespace.com/shop/p/custom-patchwork-shirt-snzgy",
        product=product,
    )

    response = client.post(
        "/api/v1/import",
        json={"product_url": "https://st-p-sews.squarespace.com/shop/p/custom-patchwork-shirt-snzgy"},
    )

    assert response.status_code == 200
    assert response.json()["platform"] == "squarespace"
    assert response.json()["title"] == "Custom Patchwork Shirt"


def test_export_shopify_csv_endpoint(monkeypatch) -> None:
    product = ProductResult(
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
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    response = client.post(
        "/api/v1/export/shopify.csv",
        json={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="shopify-20260208T000000Z.csv"'
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
    product = ProductResult(
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
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    response = client.post(
        "/api/v1/export/woocommerce.csv",
        json={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="woocommerce-20260208T000000Z.csv"'
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Type"] == "simple"
    assert frame.loc[0, "SKU"] == "SH:123"
    assert frame.loc[0, "Name"] == "Demo Mug"
    assert frame.loc[0, "Attribute 1 name"] == "Color"
    assert frame.loc[0, "Attribute 1 value(s)"] == "Black"
    assert frame.loc[0, "Stock"] == "10"
    assert frame.loc[0, "Images"] == "https://cdn.example.com/mug-front.jpg"


def test_export_squarespace_csv_endpoint(monkeypatch) -> None:
    product = ProductResult(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[
            "https://cdn.example.com/mug-front.jpg",
            "https://cdn.example.com/mug-side.jpg",
        ],
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
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    response = client.post(
        "/api/v1/export/squarespace.csv",
        json={
            "product_url": "https://demo.myshopify.com/products/mug",
            "product_page": "shop",
            "squarespace_product_url": "lemons",
        },
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="squarespace-20260208T000000Z.csv"'
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == SQUARESPACE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Product Type [Non Editable]"] == "PHYSICAL"
    assert frame.loc[0, "Product Page"] == "shop"
    assert frame.loc[0, "Product URL"] == "lemons"
    assert frame.loc[0, "Title"] == "Demo Mug"
    assert frame.loc[0, "SKU"] == "MUG-001"
    assert frame.loc[0, "Option Name 1"] == "Color"
    assert frame.loc[0, "Option Value 1"] == "Black"
    assert frame.loc[0, "Stock"] == "10"
    assert frame.loc[0, "On Sale"] == "No"
    assert frame.loc[0, "Visible"] == "No"
    assert frame.loc[0, "Hosted Image URLs"] == "https://cdn.example.com/mug-front.jpg\nhttps://cdn.example.com/mug-side.jpg"


def test_export_wix_csv_endpoint(monkeypatch) -> None:
    product = ProductResult(
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
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    response = client.post(
        "/api/v1/export/wix.csv",
        json={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="wix-20260208T000000Z.csv"'
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == WIX_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "fieldType"] == "PRODUCT"
    assert frame.loc[0, "name"] == "Demo Mug"
    assert frame.loc[0, "visible"] == "FALSE"
    assert frame.loc[0, "productOptionName[1]"] == "Color"
    assert frame.loc[0, "productOptionChoices[1]"] == "Black"
    assert frame.loc[1, "fieldType"] == "VARIANT"
    assert frame.loc[1, "sku"] == "MUG-001"
    assert frame.loc[1, "inventory"] == "10"


def test_home_page_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Ecommerce Catalog Transfer" in response.text
    assert 'action="/export.csv"' in response.text
    assert 'name="target_platform"' in response.text
    assert "<option value=\"wix\"" in response.text
    assert 'id="squarespace-fields"' in response.text
    assert "conditional-fields is-hidden" in response.text
    assert "Export CSV" in response.text
    assert "Result JSON" not in response.text


def test_web_export_csv_uses_selected_target_platform(monkeypatch) -> None:
    product = ProductResult(
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
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    response = client.post(
        "/export.csv",
        data={
            "product_url": "https://demo.myshopify.com/products/mug",
            "target_platform": "wix",
            "squarespace_product_page": "shop",
            "squarespace_product_url": "lemons",
        },
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="wix-20260208T000000Z.csv"'
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == WIX_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "fieldType"] == "PRODUCT"
    assert frame.loc[1, "fieldType"] == "VARIANT"
    assert frame.loc[1, "sku"] == "var-1"


def test_web_export_csv_invalid_target_platform_returns_error_panel(monkeypatch) -> None:
    product = ProductResult(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[],
        options={},
        variants=[],
        slug="demo-mug",
        raw={},
    )
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    response = client.post(
        "/export.csv",
        data={
            "product_url": "https://demo.myshopify.com/products/mug",
            "target_platform": "invalid",
        },
    )

    assert response.status_code == 422
    assert "Export Error" in response.text
    assert "target_platform must be one of: shopify, wix, squarespace, woocommerce" in response.text
