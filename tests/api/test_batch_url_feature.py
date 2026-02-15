import base64
import io
import json

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.models import Product, Variant, serialize_product_for_api
from app.services.exporters.shopify_csv import SHOPIFY_COLUMNS


client = TestClient(app)


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


def _patch_run_import_product(monkeypatch, url_to_product: dict[str, Product]) -> None:
    """Patch ``_run_import_product`` to return products for known URLs,
    raise HTTPException for unknown URLs.
    """
    from fastapi import HTTPException

    def fake(product_url: str) -> Product:
        if product_url in url_to_product:
            return url_to_product[product_url]
        raise HTTPException(status_code=422, detail=f"Unsupported URL: {product_url}")

    monkeypatch.setattr("app.main._run_import_product", fake)


# -------------------------------------------------------------------
# API: POST /api/v1/import — batch URL import
# -------------------------------------------------------------------

def test_api_import_single_string_returns_dict(monkeypatch) -> None:
    p = _make_product("mug-a", "Mug Alpha", "MUG-A")
    _patch_run_import_product(monkeypatch, {"https://store.test/products/mug-a": p})

    response = client.post(
        "/api/v1/import",
        json={"product_urls": "https://store.test/products/mug-a"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload["source"]["slug"] == "mug-a"
    assert payload["title"] == "Mug Alpha"


def test_api_import_backward_compat_product_url(monkeypatch) -> None:
    p = _make_product("mug-a", "Mug Alpha", "MUG-A")
    _patch_run_import_product(monkeypatch, {"https://store.test/products/mug-a": p})

    response = client.post(
        "/api/v1/import",
        json={"product_url": "https://store.test/products/mug-a"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload["source"]["slug"] == "mug-a"


def test_api_import_list_single_url_returns_dict(monkeypatch) -> None:
    p = _make_product("mug-a", "Mug Alpha", "MUG-A")
    _patch_run_import_product(monkeypatch, {"https://store.test/products/mug-a": p})

    response = client.post(
        "/api/v1/import",
        json={"product_urls": ["https://store.test/products/mug-a"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload["source"]["slug"] == "mug-a"


def test_api_import_list_multiple_urls_returns_batch(monkeypatch) -> None:
    p1 = _make_product("mug-a", "Mug Alpha", "MUG-A")
    p2 = _make_product("tee-b", "Tee Bravo", "TEE-B")
    _patch_run_import_product(monkeypatch, {
        "https://store.test/products/mug-a": p1,
        "https://store.test/products/tee-b": p2,
    })

    response = client.post(
        "/api/v1/import",
        json={"product_urls": [
            "https://store.test/products/mug-a",
            "https://store.test/products/tee-b",
        ]},
    )

    assert response.status_code == 200
    body = response.json()
    assert "products" in body
    assert "errors" in body
    assert len(body["products"]) == 2
    slugs = [p["source"]["slug"] for p in body["products"]]
    assert "mug-a" in slugs
    assert "tee-b" in slugs
    assert body["errors"] == []


def test_api_import_batch_partial_failure(monkeypatch) -> None:
    p1 = _make_product("mug-a", "Mug Alpha", "MUG-A")
    _patch_run_import_product(monkeypatch, {
        "https://store.test/products/mug-a": p1,
    })

    response = client.post(
        "/api/v1/import",
        json={"product_urls": [
            "https://store.test/products/mug-a",
            "https://store.test/products/bad-url",
        ]},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["products"]) == 1
    assert body["products"][0]["source"]["slug"] == "mug-a"
    assert len(body["errors"]) == 1
    assert body["errors"][0]["url"] == "https://store.test/products/bad-url"
    assert "detail" in body["errors"][0]


def test_api_import_batch_all_fail(monkeypatch) -> None:
    _patch_run_import_product(monkeypatch, {})

    response = client.post(
        "/api/v1/import",
        json={"product_urls": [
            "https://store.test/products/bad-a",
            "https://store.test/products/bad-b",
        ]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["products"] == []
    assert len(body["errors"]) == 2


# -------------------------------------------------------------------
# Web: POST /import.url — single URL (existing behavior)
# -------------------------------------------------------------------

def test_web_import_single_url_shows_single_editor(monkeypatch) -> None:
    p = _make_product("mug-a", "Mug Alpha", "MUG-A")
    _patch_run_import_product(monkeypatch, {"https://store.test/products/mug-a": p})

    response = client.post(
        "/import.url",
        data={"product_urls": "https://store.test/products/mug-a"},
    )

    assert response.status_code == 200
    assert "Edit Product" in response.text
    assert "data-product-editor" in response.text
    assert "data-product-editor-batch" not in response.text


# -------------------------------------------------------------------
# Web: POST /import.url — batch URL import
# -------------------------------------------------------------------

def test_web_import_multiple_urls_shows_batch_editor(monkeypatch) -> None:
    p1 = _make_product("mug-a", "Mug Alpha", "MUG-A")
    p2 = _make_product("tee-b", "Tee Bravo", "TEE-B")
    _patch_run_import_product(monkeypatch, {
        "https://store.test/products/mug-a": p1,
        "https://store.test/products/tee-b": p2,
    })

    response = client.post(
        "/import.url",
        data={"product_urls": [
            "https://store.test/products/mug-a",
            "https://store.test/products/tee-b",
        ]},
    )

    assert response.status_code == 200
    assert "Edit Products" in response.text
    assert "data-product-editor-batch" in response.text
    assert "Mug Alpha" in response.text
    assert "Tee Bravo" in response.text
    assert "(2)" in response.text
    assert "Export All as CSV" in response.text


def test_web_import_batch_partial_failure_shows_errors_and_editor(monkeypatch) -> None:
    p1 = _make_product("mug-a", "Mug Alpha", "MUG-A")
    _patch_run_import_product(monkeypatch, {
        "https://store.test/products/mug-a": p1,
    })

    response = client.post(
        "/import.url",
        data={"product_urls": [
            "https://store.test/products/mug-a",
            "https://store.test/products/bad-url",
        ]},
    )

    assert response.status_code == 200
    # Successful product shown in single editor (only 1 success)
    assert "Edit Product" in response.text
    assert "data-product-editor" in response.text
    # Partial failure errors shown
    assert "Some URLs Failed" in response.text
    assert "https://store.test/products/bad-url" in response.text


def test_web_import_batch_all_fail_shows_error(monkeypatch) -> None:
    _patch_run_import_product(monkeypatch, {})

    response = client.post(
        "/import.url",
        data={"product_urls": [
            "https://store.test/products/bad-a",
            "https://store.test/products/bad-b",
        ]},
    )

    assert response.status_code == 422
    assert "All URL imports failed" in response.text


def test_web_import_empty_urls_shows_error() -> None:
    response = client.post(
        "/import.url",
        data={"product_urls": ""},
    )

    assert response.status_code == 400
    assert "At least one product URL is required" in response.text


# -------------------------------------------------------------------
# Web: batch URL import → export roundtrip
# -------------------------------------------------------------------

def test_web_batch_url_import_then_export_roundtrip(monkeypatch) -> None:
    p1 = _make_product("mug-a", "Mug Alpha", "MUG-A")
    p2 = _make_product("tee-b", "Tee Bravo", "TEE-B")
    _patch_run_import_product(monkeypatch, {
        "https://store.test/products/mug-a": p1,
        "https://store.test/products/tee-b": p2,
    })

    preview_response = client.post(
        "/import.url",
        data={"product_urls": [
            "https://store.test/products/mug-a",
            "https://store.test/products/tee-b",
        ]},
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
            "target_platform": "shopify",
            "publish": "false",
            "weight_unit": "g",
            "bigcommerce_csv_format": "modern",
            "squarespace_product_page": "",
            "squarespace_product_url": "",
        },
    )

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    frame = pd.read_csv(io.StringIO(export_response.text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == SHOPIFY_COLUMNS
    handles = frame["Handle"].tolist()
    assert "mug-a" in handles
    assert "tee-b" in handles


# -------------------------------------------------------------------
# Web: URL page renders multiple URL inputs
# -------------------------------------------------------------------

def test_home_page_has_add_url_button() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert 'data-action="add-url"' in response.text
    assert 'data-url-input-list' in response.text
    assert '+ Add URL' in response.text


# -------------------------------------------------------------------
# Delete product buttons
# -------------------------------------------------------------------

def test_single_editor_has_delete_product_button(monkeypatch) -> None:
    p = _make_product("mug-a", "Mug Alpha", "MUG-A")
    _patch_run_import_product(monkeypatch, {"https://store.test/products/mug-a": p})

    response = client.post(
        "/import.url",
        data={"product_urls": "https://store.test/products/mug-a"},
    )

    assert response.status_code == 200
    assert "data-product-editor" in response.text
    assert 'data-action="delete-product"' in response.text


def test_batch_editor_has_delete_buttons_per_card(monkeypatch) -> None:
    p1 = _make_product("mug-a", "Mug Alpha", "MUG-A")
    p2 = _make_product("tee-b", "Tee Bravo", "TEE-B")
    _patch_run_import_product(monkeypatch, {
        "https://store.test/products/mug-a": p1,
        "https://store.test/products/tee-b": p2,
    })

    response = client.post(
        "/import.url",
        data={"product_urls": [
            "https://store.test/products/mug-a",
            "https://store.test/products/tee-b",
        ]},
    )

    assert response.status_code == 200
    assert "data-product-editor-batch" in response.text
    # Each product card should have its own delete button
    assert response.text.count('data-action="delete-batch-product"') == 2
