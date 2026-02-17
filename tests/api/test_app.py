from fastapi.testclient import TestClient
import io

import pandas as pd

from typeshift.server.main import app
from typeshift.core.exporters.platforms.bigcommerce import BIGCOMMERCE_COLUMNS
from typeshift.core.exporters.platforms.shopify import SHOPIFY_COLUMNS
from typeshift.core.exporters.platforms.squarespace import SQUARESPACE_COLUMNS
from typeshift.core.exporters.platforms.wix import WIX_COLUMNS
from typeshift.core.exporters.platforms.woocommerce import WOOCOMMERCE_COLUMNS
from typeshift.core.canonical import serialize_product_for_api
from tests.helpers._model_builders import Product, Variant
from tests.helpers._app_helpers import patch_run_import_product


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
    product = Product(
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
    payload = response.json()
    assert payload["source"]["platform"] == "shopify"
    assert payload["source"]["id"] == "123"
    assert payload["title"] == "Demo Mug"
    assert payload["price"] == {
        "current": {"amount": "12", "currency": "USD"},
        "compare_at": None,
        "cost": None,
        "min_price": None,
        "max_price": None,
    }
    assert payload.get("raw") == {}


def test_import_endpoint_accepts_woocommerce_url(monkeypatch) -> None:
    product = Product(
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
    assert response.json()["source"]["platform"] == "woocommerce"
    assert response.json()["title"] == "Adjustable Wrench Set"


def test_import_endpoint_accepts_squarespace_url(monkeypatch) -> None:
    product = Product(
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
    assert response.json()["source"]["platform"] == "squarespace"
    assert response.json()["title"] == "Custom Patchwork Shirt"


def test_import_endpoint_ignores_legacy_response_profile_query(monkeypatch) -> None:
    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[],
        options={},
        variants=[],
        raw={},
    )
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    response = client.post(
        "/api/v1/import?response_profile=legacy",
        json={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["platform"] == "shopify"
    assert payload["title"] == "Demo Mug"
    assert "source" in payload


def test_import_endpoint_ignores_invalid_response_profile_query(monkeypatch) -> None:
    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[],
        options={},
        variants=[],
        raw={},
    )
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    response = client.post(
        "/api/v1/import?response_profile=invalid",
        json={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert response.json()["source"]["platform"] == "shopify"


def test_export_shopify_csv_endpoint() -> None:
    product = Product(
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
    response = client.post(
        "/api/v1/export/shopify.csv",
        json={"product": serialize_product_for_api(product, include_raw=False)},
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


def test_export_bigcommerce_csv_endpoint() -> None:
    product = Product(
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
    response = client.post(
        "/api/v1/export/bigcommerce.csv",
        json={"product": serialize_product_for_api(product, include_raw=False)},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="bigcommerce-20260208T000000Z.csv"'
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == BIGCOMMERCE_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "Item"] == "Product"
    assert frame.loc[0, "Name"] == "Demo Mug"
    assert frame.loc[0, "SKU"] == "SH-123"
    assert frame.loc[0, "Inventory Tracking"] == "variant"
    assert frame.loc[1, "Item"] == "Variant"
    assert frame.loc[1, "SKU"] == "MUG-001"
    assert frame.loc[1, "Variant Image URL"] == "https://cdn.example.com/mug-black.jpg"
    assert frame.loc[2, "Item"] == "Image"
    assert frame.loc[2, "Image URL (Import)"] == "https://cdn.example.com/mug-front.jpg"


def test_export_bigcommerce_csv_web_endpoint(monkeypatch) -> None:
    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[],
        options={},
        variants=[Variant(id="var-1", sku="MUG-001", price_amount=12.0)],
        slug="demo-mug",
        raw={},
    )
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    response = client.post(
        "/export/bigcommerce.csv",
        data={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="bigcommerce-20260208T000000Z.csv"'
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == BIGCOMMERCE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Item"] == "Product"
    assert frame.loc[0, "SKU"] == "MUG-001"


def test_export_woocommerce_csv_endpoint() -> None:
    product = Product(
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
    response = client.post(
        "/api/v1/export/woocommerce.csv",
        json={"product": serialize_product_for_api(product, include_raw=False)},
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


def test_export_squarespace_csv_endpoint() -> None:
    product = Product(
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
    response = client.post(
        "/api/v1/export/squarespace.csv",
        json={
            "product": serialize_product_for_api(product, include_raw=False),
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


def test_export_wix_csv_endpoint() -> None:
    product = Product(
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
    response = client.post(
        "/api/v1/export/wix.csv",
        json={"product": serialize_product_for_api(product, include_raw=False)},
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
    assert frame.loc[0, "productOptionName1"] == "Color"
    assert frame.loc[0, "productOptionChoices1"] == "Black"
    assert frame.loc[1, "fieldType"] == "VARIANT"
    assert frame.loc[1, "sku"] == "MUG-001"
    assert frame.loc[1, "inventory"] == "10"


def test_export_wix_csv_endpoint_rejects_unsupported_weight_unit() -> None:
    product = Product(
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
    response = client.post(
        "/api/v1/export/wix.csv",
        json={
            "product": serialize_product_for_api(product, include_raw=False),
            "weight_unit": "oz",
        },
    )

    assert response.status_code == 422


def test_import_url_web_preview_then_export_csv(monkeypatch) -> None:
    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[],
        options={},
        variants=[Variant(id="var-1", sku="MUG-001", price_amount=12.0, inventory_quantity=5)],
        slug="demo-mug",
        raw={},
    )
    patch_run_import_product(
        monkeypatch,
        expected_url="https://demo.myshopify.com/products/mug",
        product=product,
    )

    preview_response = client.post(
        "/import.url",
        data={"product_urls": "https://demo.myshopify.com/products/mug"},
    )

    assert preview_response.status_code == 200
    assert "Edit Product" in preview_response.text

    marker = 'name="product_json_b64" value="'
    start = preview_response.text.find(marker)
    assert start != -1
    start += len(marker)
    end = preview_response.text.find('"', start)
    assert end != -1
    encoded = preview_response.text[start:end]

    export_response = client.post(
        "/export-from-product.csv",
        data={
            "product_json_b64": encoded,
            "target_platform": "woocommerce",
            "publish": "false",
            "weight_unit": "kg",
            "bigcommerce_csv_format": "modern",
            "squarespace_product_page": "",
            "squarespace_product_url": "",
        },
    )

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")


def test_web_export_csv_uses_selected_target_platform(monkeypatch) -> None:
    product = Product(
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


def test_web_export_csv_supports_bigcommerce_target(monkeypatch) -> None:
    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=["https://cdn.example.com/mug-front.jpg"],
        options={},
        variants=[Variant(id="var-1", sku="MUG-001", price_amount=12.0, inventory_quantity=5)],
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
            "target_platform": "bigcommerce",
        },
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="bigcommerce-20260208T000000Z.csv"'
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == BIGCOMMERCE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Item"] == "Product"
    assert frame.loc[0, "SKU"] == "MUG-001"
    assert frame.loc[1, "Item"] == "Image"


def test_web_export_csv_uses_selected_weight_unit_for_bigcommerce(monkeypatch) -> None:
    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[],
        options={},
        variants=[Variant(id="var-1", sku="MUG-001", price_amount=12.0, inventory_quantity=5, weight=250)],
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
            "target_platform": "bigcommerce",
            "weight_unit": "lb",
        },
    )

    assert response.status_code == 200
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert frame.loc[0, "Weight"] == "0.551156"


def test_web_export_csv_supports_bigcommerce_legacy_format(monkeypatch) -> None:
    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=["https://cdn.example.com/mug-front.jpg"],
        variants=[Variant(id="var-1", sku="MUG-001", price_amount=12.0, inventory_quantity=5)],
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
            "target_platform": "bigcommerce",
            "bigcommerce_csv_format": "legacy",
        },
    )

    assert response.status_code == 200
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert "Product Type" in frame.columns
    assert "Item" not in frame.columns
    assert frame.loc[0, "Product Type"] == "P"
    assert frame.loc[0, "Code"] == "MUG-001"


def test_export_bigcommerce_csv_endpoint_supports_legacy_format() -> None:
    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=["https://cdn.example.com/mug-front.jpg"],
        variants=[Variant(id="var-1", sku="MUG-001", price_amount=12.0, inventory_quantity=10)],
        slug="demo-mug",
        raw={},
    )
    response = client.post(
        "/api/v1/export/bigcommerce.csv",
        json={"product": serialize_product_for_api(product, include_raw=False), "csv_format": "legacy"},
    )

    assert response.status_code == 200
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert "Product Type" in frame.columns
    assert "Item" not in frame.columns
    assert frame.loc[0, "Product Type"] == "P"
    assert frame.loc[0, "Code"] == "MUG-001"


def test_web_export_csv_invalid_target_platform_returns_error_panel(monkeypatch) -> None:
    product = Product(
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
    assert "target_platform must be one of: shopify, bigcommerce, wix, squarespace, woocommerce" in response.text


def test_web_export_csv_invalid_weight_unit_returns_error_panel(monkeypatch) -> None:
    product = Product(
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
            "target_platform": "wix",
            "weight_unit": "oz",
        },
    )

    assert response.status_code == 422
    assert "Export Error" in response.text
    assert "weight_unit must be one of: kg, lb for target_platform=wix" in response.text
