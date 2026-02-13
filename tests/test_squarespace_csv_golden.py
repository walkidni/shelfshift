from pathlib import Path
from decimal import Decimal

import pandas as pd

from app.services.exporters import product_to_squarespace_csv
from app.services.exporters.squarespace_csv import SQUARESPACE_COLUMNS
from app.models import CategorySet, Inventory, Media, Money, OptionDef, OptionValue, Price, Product, Variant
from tests._csv_helpers import read_fixture_frame, read_frame


def test_squarespace_csv_matches_golden_fixture_two_variants() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "squarespace_one_product_two_variants_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == SQUARESPACE_COLUMNS

    product = Product(
        platform="shopify",
        id="101",
        title="V-Neck T-Shirt",
        description="Made of our softest blend of cotton.",
        price={"amount": 999.99, "currency": "USD"},
        images=[
            "https://cdn.example.com/legacy-wrong-image-1.jpg",
            "https://cdn.example.com/legacy-wrong-image-2.jpg",
        ],
        options={"Legacy": ["Wrong"]},
        variants=[
            Variant(
                id="v1",
                sku="SQ-TEE-S",
                options={"Legacy": "Wrong-S"},
                price_amount=111.11,
                inventory_quantity=999,
                weight=200,
                image="https://cdn.example.com/v-neck-tee-size-s.jpg",
            ),
            Variant(
                id="v2",
                sku="SQ-TEE-M",
                options={"Legacy": "Wrong-M"},
                price_amount=222.22,
                inventory_quantity=999,
                weight=200,
                image="https://cdn.example.com/v-neck-tee-size-m.jpg",
            ),
        ],
        vendor="Acme Apparel",
        category="Wrong Category",
        tags=["tee", "v-neck"],
        slug="v-neck-tee",
        raw={},
    )
    product.options_v2 = [OptionDef(name="Size", values=["S", "M"])]
    product.taxonomy_v2 = CategorySet(paths=[["Shirts"]], primary=["Shirts"])
    product.media_v2 = [
        Media(url="https://cdn.example.com/v-neck-tee.jpg", is_primary=True),
        Media(url="https://cdn.example.com/v-neck-tee-back.jpg"),
    ]
    product.variants[0].price_v2 = Price(current=Money(amount=Decimal("24.99"), currency="USD"))
    product.variants[1].price_v2 = Price(current=Money(amount=Decimal("24.99"), currency="USD"))
    product.variants[0].option_values_v2 = [OptionValue(name="Size", value="S")]
    product.variants[1].option_values_v2 = [OptionValue(name="Size", value="M")]
    product.variants[0].inventory_v2 = Inventory(track_quantity=True, quantity=10, available=True)
    product.variants[1].inventory_v2 = Inventory(track_quantity=True, quantity=8, available=True)

    csv_text, filename = product_to_squarespace_csv(
        product,
        publish=True,
        product_page="",
        product_url="v-neck-tee",
    )
    assert filename == "squarespace-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == SQUARESPACE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)


def test_squarespace_csv_matches_golden_fixture_simple_product() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "squarespace_one_simple_product_full.csv"
    expected = read_fixture_frame(fixture_path)
    assert list(expected.columns) == SQUARESPACE_COLUMNS

    product = Product(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 999.0, "currency": "USD"},
        images=[
            "https://cdn.example.com/legacy-wrong-mug-1.jpg",
            "https://cdn.example.com/legacy-wrong-mug-2.jpg",
        ],
        variants=[
            Variant(
                id="v1",
                sku="AMZ-MUG-001",
                price_amount=999.0,
                inventory_quantity=999,
                weight=250,
            )
        ],
        raw={},
    )
    product.media_v2 = [
        Media(url="https://cdn.example.com/mug-front.jpg", is_primary=True),
        Media(url="https://cdn.example.com/mug-side.jpg"),
    ]
    product.variants[0].price_v2 = Price(current=Money(amount=Decimal("12.0"), currency="USD"))
    product.variants[0].inventory_v2 = Inventory(track_quantity=True, quantity=0, available=False)

    csv_text, filename = product_to_squarespace_csv(
        product,
        publish=False,
        product_page="shop",
        product_url="demo-mug",
    )
    assert filename == "squarespace-20260208T000000Z.csv"
    actual = read_frame(csv_text)

    assert list(actual.columns) == SQUARESPACE_COLUMNS
    pd.testing.assert_frame_equal(actual, expected)
