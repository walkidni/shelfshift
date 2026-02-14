from pathlib import Path
from decimal import Decimal

import pandas as pd

from app.services.exporters import product_to_bigcommerce_csv
from app.services.exporters.bigcommerce_csv import BIGCOMMERCE_COLUMNS, BIGCOMMERCE_LEGACY_COLUMNS
from app.models import CategorySet, Inventory, Media, Money, OptionDef, OptionValue, Price
from tests._model_builders import Product, Variant
from tests._csv_helpers import read_fixture_frame, read_frame


def test_bigcommerce_csv_matches_golden_fixture_two_variants() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "bigcommerce_one_product_two_variants_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == BIGCOMMERCE_COLUMNS

    product = Product(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="<p>Soft cotton tee</p>",
        price={"amount": 999.99, "currency": "USD"},
        images=[
            "https://cdn.example.com/legacy-wrong-1.jpg",
            "https://cdn.example.com/legacy-wrong-2.jpg",
        ],
        options={"Legacy": ["Wrong"]},
        variants=[
            Variant(
                id="v1",
                sku="TEE-BLK-M",
                options={"Legacy": "Wrong-BLK"},
                price_amount=111.11,
                inventory_quantity=999,
                weight=220,
                image="https://cdn.example.com/legacy-wrong-variant-1.jpg",
            ),
            Variant(
                id="v2",
                sku="TEE-WHT-L",
                options={"Legacy": "Wrong-WHT"},
                price_amount=222.22,
                inventory_quantity=999,
                weight=230,
                image="https://cdn.example.com/legacy-wrong-variant-2.jpg",
            ),
        ],
        slug="classic-tee",
        raw={},
    )
    product.options = [
        OptionDef(name="Color", values=["Black", "White"]),
        OptionDef(name="Size", values=["M", "L"]),
    ]
    product.media = [
        Media(url="https://cdn.example.com/tee-1.jpg", is_primary=True),
        Media(url="https://cdn.example.com/tee-2.jpg"),
    ]
    product.variants[0].price = Price(current=Money(amount=Decimal("19.99"), currency="USD"))
    product.variants[1].price = Price(current=Money(amount=Decimal("21.99"), currency="USD"))
    product.variants[0].option_values = [
        OptionValue(name="Color", value="Black"),
        OptionValue(name="Size", value="M"),
    ]
    product.variants[1].option_values = [
        OptionValue(name="Color", value="White"),
        OptionValue(name="Size", value="L"),
    ]
    product.variants[0].inventory = Inventory(track_quantity=True, quantity=4, available=True)
    product.variants[1].inventory = Inventory(track_quantity=True, quantity=2, available=True)
    product.variants[0].media = [Media(url="https://cdn.example.com/tee-black-m.jpg", is_primary=True)]
    product.variants[1].media = [Media(url="https://cdn.example.com/tee-white-l.jpg", is_primary=True)]

    csv_text, filename = product_to_bigcommerce_csv(product, publish=False)
    assert filename == "bigcommerce-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == BIGCOMMERCE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_bigcommerce_csv_matches_golden_fixture_simple_product() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "bigcommerce_one_simple_product_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == BIGCOMMERCE_COLUMNS

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
                sku="MUG-001",
                price_amount=999.0,
                image="https://cdn.example.com/legacy-wrong-variant.jpg",
            )
        ],
        raw={},
    )
    product.media = [Media(url="https://cdn.example.com/mug.jpg", is_primary=True)]
    product.variants[0].price = Price(current=Money(amount=Decimal("12.0"), currency="USD"))
    product.variants[0].media = [Media(url="https://cdn.example.com/mug-variant.jpg", is_primary=True)]

    csv_text, filename = product_to_bigcommerce_csv(product, publish=True)
    assert filename == "bigcommerce-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == BIGCOMMERCE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_bigcommerce_csv_matches_golden_fixture_missing_optional_fields() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "bigcommerce_missing_optional_fields_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == BIGCOMMERCE_COLUMNS

    product = Product(
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
                inventory_quantity=0,
                weight=0,
            )
        ],
        raw={},
    )
    product.variants[0].price = Price(current=Money(amount=Decimal("19.9999"), currency="USD"))

    csv_text, filename = product_to_bigcommerce_csv(product, publish=True)
    assert filename == "bigcommerce-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == BIGCOMMERCE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_bigcommerce_csv_matches_golden_fixture_media_edge_cases() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "bigcommerce_media_edge_cases_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == BIGCOMMERCE_COLUMNS

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
                image="https://cdn.example.com/legacy-wrong-v1.jpg",
            ),
            Variant(
                id="v2",
                sku="TEE-WHT",
                options={"Legacy": "Wrong-WHT"},
                price_amount=222.0,
                inventory_quantity=999,
                image="https://cdn.example.com/legacy-wrong-v2.jpg",
            ),
        ],
        raw={},
    )
    product.options = [OptionDef(name="Color", values=["Black", "White"])]
    product.media = [
        Media(url="https://cdn.example.com/tee-1.jpg", is_primary=True),
        Media(url="https://cdn.example.com/tee-1.jpg"),
        Media(url="//cdn.example.com/tee-2.jpg"),
        Media(url="not-a-url"),
    ]
    product.variants[0].price = Price(current=Money(amount=Decimal("25.0"), currency="USD"))
    product.variants[1].price = Price(current=Money(amount=Decimal("25.0"), currency="USD"))
    product.variants[0].option_values = [OptionValue(name="Color", value="Black")]
    product.variants[1].option_values = [OptionValue(name="Color", value="White")]
    product.variants[0].inventory = Inventory(track_quantity=True, quantity=3, available=True)
    product.variants[1].inventory = Inventory(track_quantity=True, quantity=2, available=True)
    product.variants[0].media = [Media(url="//cdn.example.com/tee-black.jpg", is_primary=True)]
    product.variants[1].media = [Media(url="https://cdn.example.com/tee-white.jpg", is_primary=True)]

    csv_text, filename = product_to_bigcommerce_csv(product, publish=True)
    assert filename == "bigcommerce-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == BIGCOMMERCE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_bigcommerce_legacy_csv_matches_golden_fixture_simple_product() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "bigcommerce_legacy_one_simple_product_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == BIGCOMMERCE_LEGACY_COLUMNS

    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 999.0, "currency": "USD"},
        images=["https://cdn.example.com/legacy-wrong.jpg"],
        variants=[Variant(id="v1", sku="MUG-001", price_amount=111.0, inventory_quantity=999, weight=250)],
        category="Wrong Category",
        slug="demo-mug",
        raw={},
    )
    product.taxonomy = CategorySet(paths=[["Mugs"]], primary=["Mugs"])
    product.media = [
        Media(url="https://cdn.example.com/mug-front.jpg", is_primary=True),
        Media(url="https://cdn.example.com/mug-side.jpg"),
    ]
    product.variants[0].price = Price(current=Money(amount=Decimal("12.0"), currency="USD"))
    product.variants[0].inventory = Inventory(track_quantity=True, quantity=5, available=True)

    csv_text, filename = product_to_bigcommerce_csv(product, publish=True, csv_format="legacy")
    assert filename == "bigcommerce-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == BIGCOMMERCE_LEGACY_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)
