from pathlib import Path
from decimal import Decimal

import pandas as pd

from typeshift.core.exporters import product_to_wix_csv
from typeshift.core.exporters.platforms.wix import WIX_COLUMNS
from typeshift.core.canonical import Inventory, Media, Money, OptionDef, OptionValue, Price
from tests.helpers._model_builders import Product, Variant
from tests.helpers._csv_helpers import read_fixture_frame, read_frame

_FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "exporter" / "wix"


def test_wix_csv_matches_golden_fixture_two_variants() -> None:
    fixture_path = _FIXTURES_ROOT / "wix_one_product_two_variants_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == WIX_COLUMNS

    product = Product(
        platform="shopify",
        id="101",
        title="Guava Glow Set",
        description="Glow kit",
        price={"amount": 999.99, "currency": "USD"},
        images=["https://example.com/legacy-wrong.jpg"],
        options={"Legacy": ["Wrong"]},
        variants=[
            Variant(
                id="v1",
                sku="GG-S",
                options={"Legacy": "Wrong-S"},
                price_amount=111.11,
                inventory_quantity=999,
            ),
            Variant(
                id="v2",
                sku="GG-M",
                options={"Legacy": "Wrong-M"},
                price_amount=222.22,
                inventory_quantity=999,
            ),
        ],
        slug="guava-glow-set",
        raw={},
    )
    product.options = [OptionDef(name="Size", values=["Small", "Medium"])]
    product.media = [Media(url="https://example.com/img1.jpg", is_primary=True)]
    product.variants[0].price = Price(current=Money(amount=Decimal("29.99"), currency="USD"))
    product.variants[1].price = Price(current=Money(amount=Decimal("29.99"), currency="USD"))
    product.variants[0].option_values = [OptionValue(name="Size", value="Small")]
    product.variants[1].option_values = [OptionValue(name="Size", value="Medium")]
    product.variants[0].inventory = Inventory(track_quantity=True, quantity=10, available=True)
    product.variants[1].inventory = Inventory(track_quantity=True, quantity=8, available=True)

    csv_text, filename = product_to_wix_csv(product, publish=True)
    assert filename == "wix-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == WIX_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_wix_csv_matches_golden_fixture_simple_product() -> None:
    fixture_path = _FIXTURES_ROOT / "wix_one_simple_product_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == WIX_COLUMNS

    product = Product(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 999.0, "currency": "USD"},
        images=["https://cdn.example.com/legacy-wrong-mug.jpg"],
        variants=[
            Variant(
                id="v1",
                sku="AMZ-MUG-001",
                price_amount=999.0,
                inventory_quantity=999,
            )
        ],
        raw={},
    )
    product.media = [Media(url="https://cdn.example.com/mug.jpg", is_primary=True)]
    product.variants[0].price = Price(current=Money(amount=Decimal("12.0"), currency="USD"))
    product.variants[0].inventory = Inventory(track_quantity=True, quantity=0, available=False)

    csv_text, filename = product_to_wix_csv(product, publish=False)
    assert filename == "wix-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == WIX_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_wix_csv_matches_golden_fixture_missing_optional_fields() -> None:
    fixture_path = _FIXTURES_ROOT / "wix_missing_optional_fields_full.csv"
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
    fixture_path = _FIXTURES_ROOT / "wix_edge_numbers_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == WIX_COLUMNS

    product = Product(
        platform="shopify",
        id="90210",
        title="Precision Scale",
        description="Measures with high precision",
        price={"amount": 999.9999, "currency": "USD"},
        images=[],
        variants=[
            Variant(
                id="v1",
                sku="PRECISION-1",
                price_amount=111.1111,
                inventory_quantity=999,
                weight=333,
            )
        ],
        raw={},
    )
    product.variants[0].price = Price(current=Money(amount=Decimal("12.3456"), currency="USD"))
    product.variants[0].inventory = Inventory(track_quantity=True, quantity=0, available=False)

    csv_text, filename = product_to_wix_csv(product, publish=True)
    assert filename == "wix-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == WIX_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_wix_csv_matches_golden_fixture_media_edge_cases() -> None:
    fixture_path = _FIXTURES_ROOT / "wix_media_edge_cases_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == WIX_COLUMNS

    product = Product(
        platform="shopify",
        id="444",
        title="Media Heavy Tee",
        description="Lots of media edge cases",
        price={"amount": 999.0, "currency": "USD"},
        images=[
            "https://cdn.example.com/legacy-wrong-1.jpg",
            "https://cdn.example.com/legacy-wrong-2.jpg",
        ],
        options={"Legacy": ["Wrong"]},
        variants=[
            Variant(
                id="v1",
                sku="TEE-BLK",
                options={"Legacy": "Wrong-BLK"},
                price_amount=111.0,
                inventory_quantity=999,
            ),
            Variant(
                id="v2",
                sku="TEE-WHT",
                options={"Legacy": "Wrong-WHT"},
                price_amount=222.0,
                inventory_quantity=999,
            ),
        ],
        raw={},
    )
    product.options = [OptionDef(name="Color", values=["Black", "White"])]
    product.media = [
        Media(url="https://cdn.example.com/tee-1.jpg", is_primary=True),
        Media(url="https://cdn.example.com/tee-1.jpg"),
        Media(url="https://cdn.example.com/tee-2.jpg"),
    ]
    product.variants[0].price = Price(current=Money(amount=Decimal("25.0"), currency="USD"))
    product.variants[1].price = Price(current=Money(amount=Decimal("25.0"), currency="USD"))
    product.variants[0].option_values = [OptionValue(name="Color", value="Black")]
    product.variants[1].option_values = [OptionValue(name="Color", value="White")]
    product.variants[0].inventory = Inventory(track_quantity=True, quantity=3, available=True)
    product.variants[1].inventory = Inventory(track_quantity=True, quantity=2, available=True)

    csv_text, filename = product_to_wix_csv(product, publish=True)
    assert filename == "wix-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == WIX_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)
