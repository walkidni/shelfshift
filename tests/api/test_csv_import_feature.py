import io
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from shelfshift.server.main import app
from shelfshift.core.canonical import Product, Variant
from shelfshift.core.exporters.platforms.shopify import SHOPIFY_COLUMNS
from shelfshift.server.helpers.serialization import serialize_product_for_api


client = TestClient(app)
_FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "exporter"


def _fixture_bytes(relative_path: str) -> bytes:
    return (_FIXTURES_ROOT / relative_path).read_bytes()


def test_import_csv_shopify_returns_canonical_product() -> None:
    csv_bytes = _fixture_bytes("shopify/shopify_one_product_two_variants_full.csv")
    response = client.post(
        "/api/v1/import/csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["platform"] == "shopify"
    assert payload["source"]["slug"] == "v-neck-tee"
    assert payload["title"] == "V-Neck T-Shirt"
    assert len(payload["variants"]) == 2
    assert payload["variants"][0]["sku"] == "SQ-TEE-S"
    assert payload["variants"][1]["sku"] == "SQ-TEE-M"


def test_import_csv_requires_source_weight_unit_for_squarespace() -> None:
    csv_bytes = _fixture_bytes("squarespace/squarespace_one_simple_product_full.csv")
    response = client.post(
        "/api/v1/import/csv",
        data={"source_platform": "squarespace"},
        files={"file": ("squarespace.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 422
    assert "source_weight_unit is required" in response.json()["detail"]


def test_export_from_product_csv_returns_shopify_attachment() -> None:
    product = Product(
        source={"platform": "shopify", "id": "123", "slug": "demo-mug", "url": "https://store.test/products/demo-mug"},
        title="Demo Mug",
        description="Demo description",
        variants=[
            Variant(
                id="v1",
                sku="MUG-1",
                price={"current": {"amount": "12.5", "currency": "USD"}},
                inventory={"track_quantity": True, "quantity": 5, "available": True},
                weight={"value": "250", "unit": "g"},
            )
        ],
        price={"current": {"amount": "12.5", "currency": "USD"}},
    )
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
    assert frame.loc[0, "Variant SKU"] == "MUG-1"
