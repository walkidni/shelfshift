from decimal import Decimal

from shelfshift.core.exporters import product_to_woocommerce_csv
from shelfshift.core.exporters.platforms.woocommerce import WOOCOMMERCE_COLUMNS
from shelfshift.core.canonical import CategorySet, Inventory, Media, Money, OptionDef, OptionValue, Price
from tests.helpers._model_builders import Product, Variant
from tests.helpers._csv_helpers import read_frame


def test_simple_product_maps_qty_stock() -> None:
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
                weight=250,
            )
        ],
        raw={},
    )

    csv_text, filename = product_to_woocommerce_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert filename == "woocommerce-20260208T000000Z.csv"
    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Type"] == "simple"
    assert frame.loc[0, "SKU"] == "AMZ:b000111"
    assert frame.loc[0, "Parent"] == ""
    assert frame.loc[0, "Published"] == "0"
    assert frame.loc[0, "Short description"] == "Demo description"
    assert frame.loc[0, "Description"] == "Demo description"
    assert frame.loc[0, "Regular price"] == "12"
    assert frame.loc[0, "Weight (kg)"] == "0.25"
    assert frame.loc[0, "Stock"] == "0"
    assert frame.loc[0, "In stock?"] == "0"


def test_variable_product_uses_namespaced_parent_and_variation_skus() -> None:
    product = Product(
        platform="aliexpress",
        id="1005008518647948",
        title="Therapy Mask",
        description="Mask description",
        price={"amount": 50.4, "currency": "USD"},
        images=["https://cdn.example.com/mask-main.jpg"],
        options={"Color": ["Only Face mask", "Only Neck White"]},
        variants=[
            Variant(
                id="12000055918704602",
                sku="AE:1005008518647948:12000055918704602",
                options={"Color": "Only Face mask"},
                price_amount=50.4,
                inventory_quantity=10,
                image="https://cdn.example.com/mask-face.jpg",
            ),
            Variant(
                id="12000055918704603",
                sku="AE:1005008518647948:12000055918704603",
                options={"Color": "Only Neck White"},
                price_amount=50.4,
                inventory_quantity=0,
                image="https://cdn.example.com/mask-neck.jpg",
            ),
        ],
        raw={},
    )

    csv_text, _ = product_to_woocommerce_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "Type"] == "variable"
    assert frame.loc[0, "SKU"] == "AE:1005008518647948"
    assert frame.loc[0, "Short description"] == "Mask description"
    assert frame.loc[0, "Description"] == "Mask description"
    assert frame.loc[1, "Type"] == "variation"
    assert frame.loc[1, "SKU"] == "AE:1005008518647948:12000055918704602"
    assert frame.loc[1, "Short description"] == ""
    assert frame.loc[1, "Description"] == ""
    assert frame.loc[1, "Parent"] == "AE:1005008518647948"
    assert frame.loc[2, "SKU"] == "AE:1005008518647948:12000055918704603"
    assert frame.loc[2, "Short description"] == ""
    assert frame.loc[2, "Description"] == ""
    assert frame.loc[2, "Parent"] == "AE:1005008518647948"
    assert frame.loc[0, "Attribute 1 name"] == "Color"
    assert frame.loc[0, "Attribute 1 value(s)"] == "Only Face mask,Only Neck White"
    assert frame.loc[1, "Attribute 1 name"] == "Color"
    assert frame.loc[1, "Attribute 1 value(s)"] == "Only Face mask"
    assert frame.loc[2, "Attribute 1 value(s)"] == "Only Neck White"
    assert frame.loc[1, "Stock"] == "10"
    assert frame.loc[1, "In stock?"] == "1"
    assert frame.loc[2, "Stock"] == "0"
    assert frame.loc[2, "In stock?"] == "0"


def test_available_without_qty_does_not_emit_stock() -> None:
    product = Product(
        platform="amazon",
        id="123456789",
        title="Digital Template",
        description="PDF template",
        price={"amount": 6.5, "currency": "USD"},
        images=[],
        variants=[Variant(id="v1", price_amount=6.5, available=False, inventory_quantity=None)],
        is_digital=True,
        raw={},
    )

    csv_text, _ = product_to_woocommerce_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Type"] == "simple"
    assert frame.loc[0, "Tax status"] == "none"
    assert frame.loc[0, "In stock?"] == "0"
    assert frame.loc[0, "Stock"] == ""


def test_multiple_variants_without_options_synthesizes_option_attribute() -> None:
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

    csv_text, _ = product_to_woocommerce_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "Attribute 1 name"] == "Option"
    assert frame.loc[0, "Attribute 1 value(s)"] == "Black,White"
    assert frame.loc[1, "Attribute 1 name"] == "Option"
    assert frame.loc[1, "Attribute 1 value(s)"] == "Black"
    assert frame.loc[2, "Attribute 1 value(s)"] == "White"


def test_woocommerce_export_prefers_typed_fields_when_present() -> None:
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
                sku="TS-BLK",
                options={"Legacy": "Wrong-BLK"},
                price_amount=111.11,
                inventory_quantity=999,
                image="https://cdn.example.com/legacy-wrong-v1.jpg",
            ),
            Variant(
                id="v2",
                sku="TS-WHT",
                options={"Legacy": "Wrong-WHT"},
                price_amount=222.22,
                inventory_quantity=999,
                image="https://cdn.example.com/legacy-wrong-v2.jpg",
            ),
        ],
        raw={},
    )
    product.price = Price(current=Money(amount=Decimal("18.5"), currency="USD"))
    product.options = [OptionDef(name="Color", values=["Black", "White"])]
    product.taxonomy = CategorySet(paths=[["Men", "Shirts"]], primary=["Men", "Shirts"])
    product.media = [Media(url="https://cdn.example.com/typed-product.jpg", is_primary=True)]

    product.variants[0].price = Price(current=Money(amount=Decimal("19.99"), currency="USD"))
    product.variants[1].price = Price(current=Money(amount=Decimal("21.99"), currency="USD"))
    product.variants[0].option_values = [OptionValue(name="Color", value="Black")]
    product.variants[1].option_values = [OptionValue(name="Color", value="White")]
    product.variants[0].inventory = Inventory(track_quantity=True, quantity=4, available=True)
    product.variants[1].inventory = Inventory(track_quantity=True, quantity=2, available=True)
    product.variants[0].media = [Media(url="https://cdn.example.com/typed-v1.jpg", is_primary=True)]
    product.variants[1].media = [Media(url="https://cdn.example.com/typed-v2.jpg", is_primary=True)]

    csv_text, _ = product_to_woocommerce_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "Type"] == "variable"
    assert frame.loc[0, "Regular price"] == "18.5"
    assert frame.loc[0, "Categories"] == "Men > Shirts"
    assert frame.loc[0, "Images"] == "https://cdn.example.com/typed-product.jpg"
    assert frame.loc[0, "Attribute 1 name"] == "Color"
    assert frame.loc[0, "Attribute 1 value(s)"] == "Black,White"
    assert frame.loc[1, "Regular price"] == "19.99"
    assert frame.loc[1, "Stock"] == "4"
    assert frame.loc[1, "Images"] == "https://cdn.example.com/typed-v1.jpg"
    assert frame.loc[1, "Attribute 1 value(s)"] == "Black"
    assert frame.loc[2, "Regular price"] == "21.99"
    assert frame.loc[2, "Stock"] == "2"
    assert frame.loc[2, "Images"] == "https://cdn.example.com/typed-v2.jpg"
    assert frame.loc[2, "Attribute 1 value(s)"] == "White"
