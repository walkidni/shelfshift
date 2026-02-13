from pathlib import Path

import pandas as pd

from app.services.exporters import product_to_shopify_csv
from app.services.exporters.shopify_csv import SHOPIFY_COLUMNS
from app.services.importer import ProductResult, Variant
from tests._csv_helpers import read_fixture_frame, read_frame


def test_shopify_csv_matches_golden_fixture_two_variants() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "shopify_one_product_two_variants_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == SHOPIFY_COLUMNS

    product = ProductResult(
        platform="shopify",
        id="101",
        title="V-Neck T-Shirt",
        description="Made of our softest blend of cotton.",
        price={"amount": 24.99, "currency": "USD"},
        images=["https://cdn.example.com/v-neck-tee.jpg"],
        options={"Size": ["S", "M"]},
        variants=[
            Variant(
                id="v1",
                sku="SQ-TEE-S",
                options={"Size": "S"},
                price_amount=24.99,
                inventory_quantity=10,
                weight=200,
                image="https://cdn.example.com/v-neck-tee-size-s.jpg",
            ),
            Variant(
                id="v2",
                sku="SQ-TEE-M",
                options={"Size": "M"},
                price_amount=24.99,
                inventory_quantity=8,
                weight=200,
                image="https://cdn.example.com/v-neck-tee-size-m.jpg",
            ),
        ],
        vendor="Acme Apparel",
        category="Shirts",
        tags=["tee", "v-neck"],
        slug="v-neck-tee",
        raw={},
    )

    csv_text, filename = product_to_shopify_csv(product, publish=True)
    assert filename == "shopify-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == SHOPIFY_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_shopify_csv_matches_golden_fixture_simple_product() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "shopify_one_simple_product_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == SHOPIFY_COLUMNS

    product = ProductResult(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=["https://cdn.example.com/mug.jpg"],
        variants=[
            Variant(
                id="v1",
                sku="AMZ-MUG-001",
                price_amount=12.0,
                inventory_quantity=0,
                weight=250,
            )
        ],
        raw={},
    )

    csv_text, filename = product_to_shopify_csv(product, publish=False)
    assert filename == "shopify-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == SHOPIFY_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)
