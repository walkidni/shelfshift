from decimal import Decimal

from app.services.exporters import product_to_squarespace_csv
from app.services.exporters.squarespace_csv import SQUARESPACE_COLUMNS
from app.models import CategorySet, Inventory, Media, Money, OptionDef, OptionValue, Price, Product, Variant
from tests._csv_helpers import read_frame


def test_single_variant_maps_visible_and_hosted_images() -> None:
    product = Product(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[
            "https://cdn.example.com/mug-front.jpg",
            "https://cdn.example.com/mug-side.jpg",
        ],
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

    csv_text, filename = product_to_squarespace_csv(
        product,
        publish=False,
        product_page="shop",
        product_url="lemons",
    )
    frame = read_frame(csv_text)

    assert filename == "squarespace-20260208T000000Z.csv"
    assert list(frame.columns) == SQUARESPACE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Product Type [Non Editable]"] == "PHYSICAL"
    assert frame.loc[0, "Product Page"] == "shop"
    assert frame.loc[0, "Product URL"] == "lemons"
    assert frame.loc[0, "SKU"] == "AMZ-MUG-001"
    assert frame.loc[0, "Price"] == "12"
    assert frame.loc[0, "On Sale"] == "No"
    assert frame.loc[0, "Stock"] == "0"
    assert frame.loc[0, "Weight"] == "0.25"
    assert frame.loc[0, "Visible"] == "No"
    assert frame.loc[0, "Hosted Image URLs"] == "https://cdn.example.com/mug-front.jpg\nhttps://cdn.example.com/mug-side.jpg"


def test_multi_variant_uses_first_row_for_product_fields() -> None:
    product = Product(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="Soft cotton tee",
        price={"amount": 19.99, "currency": "USD"},
        images=["https://cdn.example.com/tee.jpg"],
        options={"Size": ["S", "M"]},
        variants=[
            Variant(
                id="v1",
                sku="TEE-S",
                options={"Size": "S"},
                price_amount=19.99,
                inventory_quantity=4,
                weight=220,
            ),
            Variant(
                id="v2",
                sku="TEE-M",
                options={"Size": "M"},
                price_amount=21.99,
                inventory_quantity=2,
                weight=230,
            ),
        ],
        category="Shirts",
        tags=["tee", "v-neck"],
        raw={},
    )

    csv_text, _ = product_to_squarespace_csv(
        product,
        publish=True,
        product_page="shop",
        product_url="pickled-things",
    )
    frame = read_frame(csv_text)

    assert list(frame.columns) == SQUARESPACE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Product Type [Non Editable]"] == "PHYSICAL"
    assert frame.loc[0, "Product Page"] == "shop"
    assert frame.loc[0, "Product URL"] == "pickled-things"
    assert frame.loc[0, "Title"] == "Classic Tee"
    assert frame.loc[0, "Description"] == "Soft cotton tee"
    assert frame.loc[0, "SKU"] == "TEE-S"
    assert frame.loc[0, "Option Name 1"] == "Size"
    assert frame.loc[0, "Option Value 1"] == "S"
    assert frame.loc[0, "Visible"] == "Yes"
    assert frame.loc[0, "Hosted Image URLs"] == "https://cdn.example.com/tee.jpg"
    assert frame.loc[1, "Product Type [Non Editable]"] == ""
    assert frame.loc[1, "Title"] == ""
    assert frame.loc[1, "Description"] == ""
    assert frame.loc[1, "SKU"] == "TEE-M"
    assert frame.loc[1, "Option Name 1"] == "Size"
    assert frame.loc[1, "Option Value 1"] == "M"
    assert frame.loc[1, "Visible"] == ""
    assert frame.loc[1, "Hosted Image URLs"] == ""


def test_multiple_variants_without_options_synthesizes_option_column() -> None:
    product = Product(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="Soft cotton tee",
        price={"amount": 19.99, "currency": "USD"},
        images=[],
        variants=[
            Variant(id="v1", sku="TEE-BLK", title="Black", price_amount=19.99),
            Variant(id="v2", sku="TEE-WHT", title="White", price_amount=21.99),
        ],
        raw={},
    )

    csv_text, _ = product_to_squarespace_csv(
        product,
        publish=False,
        product_page="shop",
        product_url="pickled-things",
    )
    frame = read_frame(csv_text)

    assert list(frame.columns) == SQUARESPACE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Option Name 1"] == "Option"
    assert frame.loc[0, "Option Value 1"] == "Black"
    assert frame.loc[1, "Option Name 1"] == "Option"
    assert frame.loc[1, "Option Value 1"] == "White"


def test_missing_inventory_defaults_to_unlimited_stock() -> None:
    product = Product(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="Soft cotton tee",
        price={"amount": 19.99, "currency": "USD"},
        images=[],
        variants=[Variant(id="v1", sku="TEE-BLK", price_amount=19.99, inventory_quantity=None)],
        raw={},
    )

    csv_text, _ = product_to_squarespace_csv(
        product,
        publish=False,
        product_page="shop",
        product_url="pickled-things",
    )
    frame = read_frame(csv_text)

    assert frame.loc[0, "Stock"] == "Unlimited"


def test_typed_fields_override_legacy_values_when_present() -> None:
    product = Product(
        platform="shopify",
        id="900",
        title="Typed Tee",
        description="Typed description",
        price={"amount": 999.99, "currency": "USD"},
        images=["https://cdn.example.com/legacy-wrong-image.jpg"],
        options={"Legacy": ["Wrong"]},
        category="Legacy Category",
        variants=[
            Variant(
                id="v-typed-1",
                sku="SQ-TYPED-1",
                options={"Legacy": "Wrong"},
                price_amount=123.45,
                inventory_quantity=None,
                image="https://cdn.example.com/legacy-wrong-variant.jpg",
            )
        ],
        raw={},
    )
    product.options_v2 = [OptionDef(name="Color", values=["Blue"])]
    product.taxonomy_v2 = CategorySet(paths=[["Men", "Shirts"]], primary=["Men", "Shirts"])
    product.media_v2 = [
        Media(url="https://cdn.example.com/typed-main.jpg", is_primary=True),
        Media(url="https://cdn.example.com/typed-gallery.jpg"),
    ]

    variant = product.variants[0]
    variant.price_v2 = Price(current=Money(amount=Decimal("12.34"), currency="USD"))
    variant.option_values_v2 = [OptionValue(name="Color", value="Blue")]
    variant.inventory_v2 = Inventory(track_quantity=True, quantity=7, available=True)

    csv_text, _ = product_to_squarespace_csv(
        product,
        publish=True,
        product_page="shop",
        product_url="typed-tee",
    )
    frame = read_frame(csv_text)

    assert list(frame.columns) == SQUARESPACE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Option Name 1"] == "Color"
    assert frame.loc[0, "Option Value 1"] == "Blue"
    assert frame.loc[0, "Price"] == "12.34"
    assert frame.loc[0, "Stock"] == "7"
    assert frame.loc[0, "Categories"] == "Men > Shirts"
    assert frame.loc[0, "Hosted Image URLs"] == "https://cdn.example.com/typed-main.jpg\nhttps://cdn.example.com/typed-gallery.jpg"
