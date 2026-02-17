import io
import json
import base64
import re
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from typeshift.server.main import app
from typeshift.core.canonical import Product, Variant, serialize_product_for_api
from typeshift.core.exporters.platforms.shopify import SHOPIFY_COLUMNS


client = TestClient(app)
_FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "exporter"


def _fixture_bytes(relative_path: str) -> bytes:
    return (_FIXTURES_ROOT / relative_path).read_bytes()


def _make_product(slug: str, title: str, sku: str) -> Product:
    return Product(
        source={"platform": "shopify", "id": slug, "slug": slug, "url": f"https://store.test/products/{slug}"},
        title=title,
        description=f"{title} description",
        variants=[
            Variant(
                id=f"v-{sku}",
                sku=sku,
                price={"current": {"amount": "10", "currency": "USD"}},
                inventory={"track_quantity": True, "quantity": 5, "available": True},
                weight={"value": "200", "unit": "g"},
            )
        ],
        price={"current": {"amount": "10", "currency": "USD"}},
    )


# -------------------------------------------------------------------
# API: POST /api/v1/import/csv — batch detection
# -------------------------------------------------------------------

def test_import_csv_api_single_product_returns_dict() -> None:
    csv_bytes = _fixture_bytes("shopify/shopify_one_product_two_variants_full.csv")
    response = client.post(
        "/api/v1/import/csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload["source"]["slug"] == "v-neck-tee"


def test_import_csv_api_batch_returns_list() -> None:
    csv_bytes = _fixture_bytes("shopify/shopify_two_products_batch.csv")
    response = client.post(
        "/api/v1/import/csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 2
    slugs = [p["source"]["slug"] for p in payload]
    assert "mug-a" in slugs
    assert "tee-b" in slugs


# -------------------------------------------------------------------
# API: POST /api/v1/export/from-product.csv — batch export
# -------------------------------------------------------------------

def test_export_from_product_csv_api_single_still_works() -> None:
    product = _make_product("demo-mug", "Demo Mug", "MUG-1")
    payload = {
        "product": serialize_product_for_api(product, include_raw=False),
        "target_platform": "shopify",
        "publish": True,
        "weight_unit": "g",
    }
    response = client.post("/api/v1/export/from-product.csv", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert frame.loc[0, "Handle"] == "demo-mug"


def test_export_from_product_csv_api_batch() -> None:
    p1 = _make_product("mug-a", "Mug Alpha", "MUG-A")
    p2 = _make_product("tee-b", "Tee Bravo", "TEE-B")
    payload = {
        "product": [
            serialize_product_for_api(p1, include_raw=False),
            serialize_product_for_api(p2, include_raw=False),
        ],
        "target_platform": "shopify",
        "publish": False,
        "weight_unit": "g",
    }
    response = client.post("/api/v1/export/from-product.csv", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == SHOPIFY_COLUMNS
    handles = frame["Handle"].tolist()
    assert "mug-a" in handles
    assert "tee-b" in handles


# -------------------------------------------------------------------
# Web: POST /import.csv — batch detection
# -------------------------------------------------------------------

def test_import_csv_web_single_product_shows_single_editor() -> None:
    csv_bytes = _fixture_bytes("shopify/shopify_one_simple_product_full.csv")
    response = client.post(
        "/import.csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    assert "Edit Product" in response.text
    assert "data-product-editor" in response.text
    assert "data-product-editor-batch" not in response.text


def test_import_csv_web_batch_shows_batch_editor() -> None:
    csv_bytes = _fixture_bytes("shopify/shopify_two_products_batch.csv")
    response = client.post(
        "/import.csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    assert "Edit Products" in response.text
    assert "data-product-editor-batch" in response.text
    assert "Mug Alpha" in response.text
    assert "Tee Bravo" in response.text


def test_import_csv_web_batch_renders_product_count() -> None:
    csv_bytes = _fixture_bytes("shopify/shopify_two_products_batch.csv")
    response = client.post(
        "/import.csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    assert "(2)" in response.text
    assert "Export All as CSV" in response.text


# -------------------------------------------------------------------
# Web: POST /export-from-product.csv — batch export via b64
# -------------------------------------------------------------------

def test_export_from_product_csv_web_batch() -> None:
    p1 = _make_product("mug-a", "Mug Alpha", "MUG-A")
    p2 = _make_product("tee-b", "Tee Bravo", "TEE-B")
    products_payload = [
        serialize_product_for_api(p1, include_raw=False),
        serialize_product_for_api(p2, include_raw=False),
    ]
    encoded = base64.b64encode(json.dumps(products_payload).encode("utf-8")).decode("utf-8")

    response = client.post(
        "/export-from-product.csv",
        data={
            "product_json_b64": encoded,
            "target_platform": "shopify",
            "publish": "false",
            "weight_unit": "g",
            "bigcommerce_csv_format": "modern",
            "squarespace_product_page": "",
            "squarespace_product_url": "",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False)
    handles = frame["Handle"].tolist()
    assert "mug-a" in handles
    assert "tee-b" in handles


def test_import_csv_web_batch_then_export_roundtrip() -> None:
    csv_bytes = _fixture_bytes("shopify/shopify_two_products_batch.csv")
    preview_response = client.post(
        "/import.csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_bytes, "text/csv")},
    )

    assert preview_response.status_code == 200

    marker = 'name="product_json_b64" value="'
    start = preview_response.text.find(marker)
    assert start != -1, "product_json_b64 hidden input not found"
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


# -------------------------------------------------------------------
# Delete product buttons — CSV editors
# -------------------------------------------------------------------

def test_csv_single_editor_has_delete_button() -> None:
    csv_bytes = _fixture_bytes("shopify/shopify_one_simple_product_full.csv")
    response = client.post(
        "/import.csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    assert "data-product-editor" in response.text
    assert 'data-action="delete-product"' in response.text


def test_csv_batch_editor_has_delete_buttons_per_card() -> None:
    csv_bytes = _fixture_bytes("shopify/shopify_two_products_batch.csv")
    response = client.post(
        "/import.csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    assert "data-product-editor-batch" in response.text
    assert response.text.count('data-action="delete-batch-product"') == 2
