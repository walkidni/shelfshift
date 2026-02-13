from pathlib import Path

import pandas as pd

from app.services.exporters import product_to_bigcommerce_csv
from app.services.exporters.bigcommerce_csv import BIGCOMMERCE_COLUMNS
from app.services.importer import ProductResult, Variant
from tests._csv_helpers import read_fixture_frame, read_frame


def test_bigcommerce_csv_matches_golden_fixture_two_variants() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "bigcommerce_one_product_two_variants_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == BIGCOMMERCE_COLUMNS

    product = ProductResult(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="<p>Soft cotton tee</p>",
        price={"amount": 19.99, "currency": "USD"},
        images=[
            "https://cdn.example.com/tee-1.jpg",
            "https://cdn.example.com/tee-2.jpg",
        ],
        options={"Color": ["Black", "White"], "Size": ["M", "L"]},
        variants=[
            Variant(
                id="v1",
                sku="TEE-BLK-M",
                options={"Color": "Black", "Size": "M"},
                price_amount=19.99,
                inventory_quantity=4,
                weight=220,
                image="https://cdn.example.com/tee-black-m.jpg",
            ),
            Variant(
                id="v2",
                sku="TEE-WHT-L",
                options={"Color": "White", "Size": "L"},
                price_amount=21.99,
                inventory_quantity=2,
                weight=230,
                image="//cdn.example.com/tee-white-l.jpg",
            ),
        ],
        slug="classic-tee",
        raw={},
    )

    csv_text, filename = product_to_bigcommerce_csv(product, publish=False)
    assert filename == "bigcommerce-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == BIGCOMMERCE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_bigcommerce_csv_matches_golden_fixture_simple_product() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "bigcommerce_one_simple_product_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == BIGCOMMERCE_COLUMNS

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
                sku="MUG-001",
                price_amount=12.0,
                image="//cdn.example.com/mug-variant.jpg",
            )
        ],
        raw={},
    )

    csv_text, filename = product_to_bigcommerce_csv(product, publish=True)
    assert filename == "bigcommerce-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == BIGCOMMERCE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_bigcommerce_csv_matches_golden_fixture_missing_optional_fields() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "bigcommerce_missing_optional_fields_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == BIGCOMMERCE_COLUMNS

    product = ProductResult(
        platform="shopify",
        id="321",
        title="Minimal Product",
        description=None,
        price=None,
        images=[],
        variants=[],
        raw={},
    )

    csv_text, filename = product_to_bigcommerce_csv(product, publish=False)
    assert filename == "bigcommerce-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == BIGCOMMERCE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_bigcommerce_csv_matches_golden_fixture_edge_numbers() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "bigcommerce_edge_numbers_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == BIGCOMMERCE_COLUMNS

    product = ProductResult(
        platform="shopify",
        id="90210",
        title="Precision Scale",
        description="Measures with high precision",
        price={"amount": 19.9999, "currency": "USD"},
        images=[],
        variants=[
            Variant(
                id="v1",
                sku="PRECISION-1",
                price_amount=19.9999,
                inventory_quantity=0,
                weight=0,
            )
        ],
        raw={},
    )

    csv_text, filename = product_to_bigcommerce_csv(product, publish=True)
    assert filename == "bigcommerce-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == BIGCOMMERCE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_bigcommerce_csv_matches_golden_fixture_media_edge_cases() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "bigcommerce_media_edge_cases_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == BIGCOMMERCE_COLUMNS

    product = ProductResult(
        platform="shopify",
        id="444",
        title="Media Heavy Tee",
        description="Lots of media edge cases",
        price={"amount": 25.0, "currency": "USD"},
        images=[
            "https://cdn.example.com/tee-1.jpg",
            "https://cdn.example.com/tee-1.jpg",
            "//cdn.example.com/tee-2.jpg",
            "not-a-url",
        ],
        options={"Color": ["Black", "White"]},
        variants=[
            Variant(
                id="v1",
                sku="TEE-BLK",
                options={"Color": "Black"},
                price_amount=25.0,
                inventory_quantity=3,
                image="//cdn.example.com/tee-black.jpg",
            ),
            Variant(
                id="v2",
                sku="TEE-WHT",
                options={"Color": "White"},
                price_amount=25.0,
                inventory_quantity=2,
                image="https://cdn.example.com/tee-white.jpg",
            ),
        ],
        raw={},
    )

    csv_text, filename = product_to_bigcommerce_csv(product, publish=True)
    assert filename == "bigcommerce-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == BIGCOMMERCE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)
