from decimal import Decimal

from typeshift.core.exporters import product_to_bigcommerce_csv
from typeshift.core.exporters.platforms.bigcommerce import BIGCOMMERCE_COLUMNS, BIGCOMMERCE_LEGACY_COLUMNS
from typeshift.core.canonical import CategorySet, Inventory, Media, Money, OptionDef, OptionValue, Price
from tests.helpers._model_builders import Product, Variant
from tests.helpers._csv_helpers import read_frame


def test_bigcommerce_export_emits_modern_v3_product_variant_image_rows() -> None:
    product = Product(
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
    frame = read_frame(csv_text)

    assert filename == "bigcommerce-20260208T000000Z.csv"
    assert list(frame.columns) == BIGCOMMERCE_COLUMNS
    assert len(frame) == 5

    assert frame.loc[0, "Item"] == "Product"
    assert frame.loc[0, "Type"] == "physical"
    assert frame.loc[0, "Name"] == "Classic Tee"
    assert frame.loc[0, "Description"] == "<p>Soft cotton tee</p>"
    assert frame.loc[0, "SKU"] == "SH-101"
    assert frame.loc[0, "Price"] == "19.99"
    assert frame.loc[0, "Categories"] == ""
    assert frame.loc[0, "Weight"] == "0.22"
    assert frame.loc[0, "Inventory Tracking"] == "variant"
    assert frame.loc[0, "Current Stock"] == "0"
    assert frame.loc[0, "Low Stock"] == "0"
    assert frame.loc[0, "Product URL"] == "/classic-tee/"
    assert frame.loc[0, "Is Visible"] == "FALSE"
    assert frame.loc[0, "Tax Class"] == "0"

    assert frame.loc[1, "Item"] == "Variant"
    assert frame.loc[1, "SKU"] == "TEE-BLK-M"
    assert frame.loc[1, "Options"] == "Type=Rectangle|Name=Color|Value=BlackType=Rectangle|Name=Size|Value=M"
    assert frame.loc[1, "Current Stock"] == "4"
    assert frame.loc[1, "Variant Image URL"] == "https://cdn.example.com/tee-black-m.jpg"

    assert frame.loc[2, "Item"] == "Variant"
    assert frame.loc[2, "SKU"] == "TEE-WHT-L"
    assert frame.loc[2, "Options"] == "Type=Rectangle|Name=Color|Value=WhiteType=Rectangle|Name=Size|Value=L"
    assert frame.loc[2, "Current Stock"] == "2"
    assert frame.loc[2, "Variant Image URL"] == "https://cdn.example.com/tee-white-l.jpg"

    assert frame.loc[3, "Item"] == "Image"
    assert frame.loc[3, "Image URL (Import)"] == "https://cdn.example.com/tee-1.jpg"
    assert frame.loc[3, "Image is Thumbnail"] == "TRUE"
    assert frame.loc[3, "Image Sort Order"] == "0"

    assert frame.loc[4, "Item"] == "Image"
    assert frame.loc[4, "Image URL (Import)"] == "https://cdn.example.com/tee-2.jpg"
    assert frame.loc[4, "Image is Thumbnail"] == "FALSE"
    assert frame.loc[4, "Image Sort Order"] == "1"


def test_bigcommerce_export_simple_product_uses_product_and_image_rows() -> None:
    product = Product(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=["https://cdn.example.com/mug.jpg"],
        variants=[Variant(id="v1", sku="MUG-001", price_amount=12.0, image="//cdn.example.com/mug-variant.jpg")],
        raw={},
    )

    csv_text, _ = product_to_bigcommerce_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == BIGCOMMERCE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Item"] == "Product"
    assert frame.loc[0, "Type"] == "physical"
    assert frame.loc[0, "SKU"] == "MUG-001"
    assert frame.loc[0, "Price"] == "12"
    assert frame.loc[0, "Inventory Tracking"] == "none"
    assert frame.loc[0, "Current Stock"] == "0"
    assert frame.loc[0, "Weight"] == "0"
    assert frame.loc[0, "Variant Image URL"] == "https://cdn.example.com/mug-variant.jpg"
    assert frame.loc[0, "Product URL"] == "/demo-mug/"
    assert frame.loc[0, "Is Visible"] == "TRUE"
    assert frame.loc[0, "Tax Class"] == "0"
    assert frame.loc[1, "Item"] == "Image"
    assert frame.loc[1, "Image URL (Import)"] == "https://cdn.example.com/mug.jpg"


def test_bigcommerce_export_uses_swatch_only_when_value_data_is_present() -> None:
    product = Product(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="Demo description",
        price={"amount": 19.99, "currency": "USD"},
        options={
            "Color": ["Black[#000000]"],
            "Size": ["M"],
        },
        variants=[
            Variant(
                id="v1",
                sku="TEE-BLK-M",
                options={"Color": "Black[#000000]", "Size": "M"},
                price_amount=19.99,
            )
        ],
        raw={},
    )

    csv_text, _ = product_to_bigcommerce_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert frame.loc[0, "Item"] == "Product"
    assert frame.loc[1, "Item"] == "Variant"
    assert frame.loc[1, "Options"] == "Type=Swatch|Name=Color|Value=Black[#000000]Type=Rectangle|Name=Size|Value=M"


def test_bigcommerce_export_uses_product_weight_when_variant_weight_missing() -> None:
    product = Product(
        platform="aliexpress",
        id="1005008518647948",
        title="LED Mask",
        description="Demo description",
        price={"amount": 50.4, "currency": "USD"},
        variants=[
            Variant(
                id="12000055918704599",
                sku="AE:1005008518647948:12000055918704599",
                price_amount=50.4,
                weight=None,
            )
        ],
        weight=100.0,
        raw={},
    )

    csv_text, _ = product_to_bigcommerce_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert frame.loc[0, "Item"] == "Product"
    assert frame.loc[0, "Weight"] == "0.1"


def test_bigcommerce_export_supports_lb_weight_unit() -> None:
    product = Product(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="Demo description",
        price={"amount": 19.99, "currency": "USD"},
        variants=[
            Variant(
                id="v1",
                sku="TEE-BLK-M",
                price_amount=19.99,
                weight=220,
            )
        ],
        raw={},
    )

    csv_text, _ = product_to_bigcommerce_csv(product, publish=False, weight_unit="lb")
    frame = read_frame(csv_text)

    assert frame.loc[0, "Item"] == "Product"
    assert frame.loc[0, "Weight"] == "0.485017"


def test_bigcommerce_export_supports_legacy_format_opt_in() -> None:
    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=["https://cdn.example.com/mug-front.jpg", "https://cdn.example.com/mug-side.jpg"],
        variants=[Variant(id="v1", sku="MUG-001", price_amount=12.0, inventory_quantity=5, weight=250)],
        category="Mugs",
        slug="demo-mug",
        raw={},
    )

    csv_text, filename = product_to_bigcommerce_csv(product, publish=True, csv_format="legacy")
    frame = read_frame(csv_text)

    assert filename == "bigcommerce-20260208T000000Z.csv"
    assert list(frame.columns) == BIGCOMMERCE_LEGACY_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Product Type"] == "P"
    assert frame.loc[0, "Code"] == "MUG-001"
    assert frame.loc[0, "Name"] == "Demo Mug"
    assert frame.loc[0, "Calculated Price"] == "12"
    assert frame.loc[0, "Product Visible"] == "Y"
    assert frame.loc[0, "Product URL"] == "/demo-mug/"
    assert frame.loc[0, "Images"] == "Product Image URL: https://cdn.example.com/mug-front.jpg|Product Image URL: https://cdn.example.com/mug-side.jpg"


def test_bigcommerce_export_uses_modern_format_by_default() -> None:
    product = Product(
        platform="shopify",
        id="123",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        variants=[Variant(id="v1", sku="MUG-001", price_amount=12.0)],
        raw={},
    )

    csv_text, _ = product_to_bigcommerce_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == BIGCOMMERCE_COLUMNS


def test_bigcommerce_modern_prefers_typed_fields_when_present() -> None:
    product = Product(
        platform="shopify",
        id="900",
        title="Typed Tee",
        description="Typed description",
        price={"amount": 999.99, "currency": "USD"},
        images=["https://cdn.example.com/legacy-wrong-product.jpg"],
        options={"Legacy": ["Wrong"]},
        category="Legacy Category",
        variants=[
            Variant(
                id="v1",
                sku="TEE-TYPED",
                options={"Legacy": "Wrong"},
                price_amount=111.11,
                inventory_quantity=999,
                image="https://cdn.example.com/legacy-wrong-variant.jpg",
            )
        ],
        raw={},
    )
    product.options = [OptionDef(name="Color", values=["Blue"])]
    product.taxonomy = CategorySet(paths=[["Men", "Shirts"]], primary=["Men", "Shirts"])
    product.media = [
        Media(url="https://cdn.example.com/typed-product-1.jpg", is_primary=True),
        Media(url="https://cdn.example.com/typed-product-2.jpg"),
    ]
    variant = product.variants[0]
    variant.option_values = [OptionValue(name="Color", value="Blue")]
    variant.price = Price(current=Money(amount=Decimal("12.34"), currency="USD"))
    variant.inventory = Inventory(track_quantity=True, quantity=7, available=True)
    variant.media = [Media(url="https://cdn.example.com/typed-variant.jpg", is_primary=True)]

    csv_text, _ = product_to_bigcommerce_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert frame.loc[0, "Item"] == "Product"
    assert frame.loc[0, "Price"] == "12.34"
    assert frame.loc[0, "Categories"] == ""
    assert frame.loc[1, "Item"] == "Variant"
    assert frame.loc[1, "Options"] == "Type=Rectangle|Name=Color|Value=Blue"
    assert frame.loc[1, "Current Stock"] == "7"
    assert frame.loc[1, "Variant Image URL"] == "https://cdn.example.com/typed-variant.jpg"
    assert frame.loc[2, "Item"] == "Image"
    assert frame.loc[2, "Image URL (Import)"] == "https://cdn.example.com/typed-product-1.jpg"
    assert frame.loc[3, "Item"] == "Image"
    assert frame.loc[3, "Image URL (Import)"] == "https://cdn.example.com/typed-product-2.jpg"


def test_bigcommerce_legacy_prefers_typed_fields_when_present() -> None:
    product = Product(
        platform="shopify",
        id="901",
        title="Typed Mug",
        description="Typed description",
        price={"amount": 999.0, "currency": "USD"},
        images=["https://cdn.example.com/legacy-wrong-1.jpg"],
        category="Legacy Category",
        variants=[
            Variant(
                id="v1",
                sku="MUG-TYPED",
                price_amount=111.0,
                inventory_quantity=999,
            )
        ],
        raw={},
    )
    product.taxonomy = CategorySet(paths=[["Drinkware", "Mugs"]], primary=["Drinkware", "Mugs"])
    product.media = [Media(url="https://cdn.example.com/typed-mug.jpg", is_primary=True)]
    variant = product.variants[0]
    variant.price = Price(current=Money(amount=Decimal("12.0"), currency="USD"))
    variant.inventory = Inventory(track_quantity=True, quantity=5, available=True)

    csv_text, _ = product_to_bigcommerce_csv(product, publish=True, csv_format="legacy")
    frame = read_frame(csv_text)

    assert list(frame.columns) == BIGCOMMERCE_LEGACY_COLUMNS
    assert frame.loc[0, "Calculated Price"] == "12"
    assert frame.loc[0, "Stock Level"] == "5"
    assert (
        frame.loc[0, "Category Details"]
        == "Category Name: Drinkware > Mugs, Category Path: Drinkware > Mugs"
    )
    assert frame.loc[0, "Images"] == "Product Image URL: https://cdn.example.com/typed-mug.jpg"
