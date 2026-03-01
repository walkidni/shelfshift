from fastapi.testclient import TestClient

from shelfshift.server.main import app
from shelfshift.core.canonical import Product, Variant


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

    monkeypatch.setattr("shelfshift.server.helpers.importing.run_import_product", fake)


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
