import io
import json
import base64
import html
import re
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.models import Product, Variant, serialize_product_for_api
from app.services.exporters.shopify_csv import SHOPIFY_COLUMNS


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


def test_import_csv_web_preview_then_export_csv() -> None:
    csv_bytes = _fixture_bytes("shopify/shopify_one_simple_product_full.csv")
    preview_response = client.post(
        "/import.csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_bytes, "text/csv")},
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
    product_json = json.loads(base64.b64decode(encoded.encode("utf-8")).decode("utf-8"))

    export_response = client.post(
        "/export-from-product.csv",
        data={
            "product_json_b64": base64.b64encode(json.dumps(product_json).encode("utf-8")).decode("utf-8"),
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


def test_import_csv_web_preview_renders_editable_payload_and_export_payload() -> None:
    long_description = "X" * 1200
    csv_text = "\n".join(
        [
            "Handle,Title,Body (HTML),Variant SKU,Variant Price",
            f"demo-handle,Demo Product,{long_description},DEMO-SKU,19.99",
        ]
    )
    preview_response = client.post(
        "/import.csv",
        data={"source_platform": "shopify"},
        files={"file": ("shopify.csv", csv_text.encode("utf-8"), "text/csv")},
    )

    assert preview_response.status_code == 200

    editor_match = re.search(
        r'<script type="application/json" id="editor-product-payload">(.*?)</script>',
        preview_response.text,
        flags=re.DOTALL,
    )
    assert editor_match is not None
    editor_payload = json.loads(html.unescape(editor_match.group(1)))

    marker = 'name="product_json_b64" value="'
    start = preview_response.text.find(marker)
    assert start != -1
    start += len(marker)
    end = preview_response.text.find('"', start)
    assert end != -1
    encoded = preview_response.text[start:end]
    hidden_payload = json.loads(base64.b64decode(encoded.encode("utf-8")).decode("utf-8"))

    assert hidden_payload["description"] == long_description
    assert hidden_payload["seo"]["description"] == long_description
    assert editor_payload["description"] == long_description
    assert editor_payload["seo"]["description"] == long_description
