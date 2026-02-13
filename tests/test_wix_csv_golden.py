from pathlib import Path

import pandas as pd

from app.services.exporters import product_to_wix_csv
from app.services.exporters.wix_csv import WIX_COLUMNS
from app.models import Product, Variant
from tests._csv_helpers import read_fixture_frame, read_frame


def test_wix_csv_matches_golden_fixture_two_variants() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "wix_one_product_two_variants_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == WIX_COLUMNS

    product = Product(
        platform="shopify",
        id="101",
        title="Guava Glow Set",
        description="Glow kit",
        price={"amount": 29.99, "currency": "USD"},
        images=["https://example.com/img1.jpg"],
        options={"Size": ["Small", "Medium"]},
        variants=[
            Variant(
                id="v1",
                sku="GG-S",
                options={"Size": "Small"},
                price_amount=29.99,
                inventory_quantity=10,
            ),
            Variant(
                id="v2",
                sku="GG-M",
                options={"Size": "Medium"},
                price_amount=29.99,
                inventory_quantity=8,
            ),
        ],
        slug="guava-glow-set",
        raw={},
    )

    csv_text, filename = product_to_wix_csv(product, publish=True)
    assert filename == "wix-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == WIX_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_wix_csv_matches_golden_fixture_simple_product() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "wix_one_simple_product_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == WIX_COLUMNS

    product = Product(
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
            )
        ],
        raw={},
    )

    csv_text, filename = product_to_wix_csv(product, publish=False)
    assert filename == "wix-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == WIX_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_wix_csv_matches_golden_fixture_missing_optional_fields() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "wix_missing_optional_fields_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == WIX_COLUMNS

    product = Product(
        platform="shopify",
        id="321",
        title=None,
        description=None,
        price=None,
        images=[],
        variants=[],
        raw={},
    )

    csv_text, filename = product_to_wix_csv(product, publish=False)
    assert filename == "wix-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == WIX_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_wix_csv_matches_golden_fixture_edge_numbers() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "wix_edge_numbers_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == WIX_COLUMNS

    product = Product(
        platform="shopify",
        id="90210",
        title="Precision Scale",
        description="Measures with high precision",
        price={"amount": 12.3456, "currency": "USD"},
        images=[],
        variants=[
            Variant(
                id="v1",
                sku="PRECISION-1",
                price_amount=12.3456,
                inventory_quantity=0,
                weight=333,
            )
        ],
        raw={},
    )

    csv_text, filename = product_to_wix_csv(product, publish=True)
    assert filename == "wix-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == WIX_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_wix_csv_matches_golden_fixture_media_edge_cases() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "wix_media_edge_cases_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == WIX_COLUMNS

    product = Product(
        platform="shopify",
        id="444",
        title="Media Heavy Tee",
        description="Lots of media edge cases",
        price={"amount": 25.0, "currency": "USD"},
        images=[
            "https://cdn.example.com/tee-1.jpg",
            "https://cdn.example.com/tee-1.jpg",
            "https://cdn.example.com/tee-2.jpg",
        ],
        options={"Color": ["Black", "White"]},
        variants=[
            Variant(
                id="v1",
                sku="TEE-BLK",
                options={"Color": "Black"},
                price_amount=25.0,
                inventory_quantity=3,
            ),
            Variant(
                id="v2",
                sku="TEE-WHT",
                options={"Color": "White"},
                price_amount=25.0,
                inventory_quantity=2,
            ),
        ],
        raw={},
    )

    csv_text, filename = product_to_wix_csv(product, publish=True)
    assert filename == "wix-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == WIX_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)
