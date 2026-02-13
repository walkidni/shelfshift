from decimal import Decimal

from app.services.exporters import product_to_wix_csv
from app.services.exporters.wix_csv import WIX_COLUMNS
from app.models import Inventory, Media, Money, OptionDef, OptionValue, Price, Product, Variant
from tests._csv_helpers import read_frame


def test_wix_export_maps_product_and_variant_rows() -> None:
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
    frame = read_frame(csv_text)

    assert filename == "wix-20260208T000000Z.csv"
    assert list(frame.columns) == WIX_COLUMNS
    assert len(frame) == 3

    assert frame.loc[0, "handle"] == "guava-glow-set"
    assert frame.loc[0, "fieldType"] == "PRODUCT"
    assert frame.loc[0, "name"] == "Guava Glow Set"
    assert frame.loc[0, "visible"] == "TRUE"
    assert frame.loc[0, "plainDescription"] == "Glow kit"
    assert frame.loc[0, "price"] == "29.99"
    assert frame.loc[0, "productOptionName1"] == "Size"
    assert frame.loc[0, "productOptionType1"] == "TEXT_CHOICES"
    assert frame.loc[0, "productOptionChoices1"] == "Small;Medium"
    assert frame.loc[0, "media"] == "https://example.com/img1.jpg"

    assert frame.loc[1, "fieldType"] == "VARIANT"
    assert frame.loc[1, "sku"] == "GG-S"
    assert frame.loc[1, "inventory"] == "10"
    assert frame.loc[1, "productOptionChoices1"] == "Small"

    assert frame.loc[2, "fieldType"] == "VARIANT"
    assert frame.loc[2, "sku"] == "GG-M"
    assert frame.loc[2, "inventory"] == "8"
    assert frame.loc[2, "productOptionChoices1"] == "Medium"


def test_wix_export_synthesizes_option_column_when_variants_have_no_options() -> None:
    product = Product(
        platform="aliexpress",
        id="1005008518647948",
        title="Therapy Mask",
        description="Mask",
        price={"amount": 50.4, "currency": "USD"},
        images=[],
        variants=[
            Variant(id="v1", sku="AE-1", title="Only Face mask", price_amount=50.4),
            Variant(id="v2", sku="AE-2", title="Only Neck White", price_amount=60.4),
        ],
        raw={},
    )

    csv_text, _ = product_to_wix_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WIX_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "fieldType"] == "PRODUCT"
    assert frame.loc[0, "visible"] == "FALSE"
    assert frame.loc[0, "productOptionName1"] == "Option"
    assert frame.loc[0, "productOptionChoices1"] == "Only Face mask;Only Neck White"
    assert frame.loc[1, "productOptionChoices1"] == "Only Face mask"
    assert frame.loc[2, "productOptionChoices1"] == "Only Neck White"


def test_wix_export_emits_media_rows_for_additional_images() -> None:
    product = Product(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="Soft cotton tee",
        price={"amount": 19.99, "currency": "USD"},
        images=[
            "https://cdn.example.com/tee-1.jpg",
            "https://cdn.example.com/tee-2.jpg",
            "https://cdn.example.com/tee-3.jpg",
        ],
        variants=[Variant(id="v1", sku="TEE-1", price_amount=19.99, inventory_quantity=4)],
        raw={},
    )

    csv_text, _ = product_to_wix_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WIX_COLUMNS
    assert len(frame) == 4
    assert frame.loc[0, "fieldType"] == "PRODUCT"
    assert frame.loc[0, "media"] == "https://cdn.example.com/tee-1.jpg"
    assert frame.loc[2, "fieldType"] == "MEDIA"
    assert frame.loc[2, "media"] == "https://cdn.example.com/tee-2.jpg"
    assert frame.loc[3, "fieldType"] == "MEDIA"
    assert frame.loc[3, "media"] == "https://cdn.example.com/tee-3.jpg"


def test_wix_export_truncates_name_and_plain_description_to_wix_limits() -> None:
    product = Product(
        platform="shopify",
        id="101",
        title="X" * 114,
        description="Y" * 21649,
        price={"amount": 19.99, "currency": "USD"},
        images=["https://cdn.example.com/tee-1.jpg"],
        variants=[Variant(id="v1", sku="TEE-1", price_amount=19.99, inventory_quantity=4)],
        raw={},
    )

    csv_text, _ = product_to_wix_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert len(frame.loc[0, "name"]) == 80
    assert len(frame.loc[0, "plainDescription"]) == 16000
    assert frame.loc[0, "name"] == "X" * 80
    assert frame.loc[0, "plainDescription"] == "Y" * 16000


def test_wix_export_truncates_using_utf16_units_for_wix_limits() -> None:
    # Python len("A" * 15999 + "😀") == 16000, but JS/UTF-16 length is 16001.
    description = ("A" * 15999) + "😀" + ("B" * 50)
    name = ("N" * 79) + "😀"
    product = Product(
        platform="shopify",
        id="101",
        title=name,
        description=description,
        price={"amount": 19.99, "currency": "USD"},
        images=["https://cdn.example.com/tee-1.jpg"],
        variants=[Variant(id="v1", sku="TEE-1", price_amount=19.99, inventory_quantity=4)],
        raw={},
    )

    csv_text, _ = product_to_wix_csv(product, publish=True)
    frame = read_frame(csv_text)

    exported_name = frame.loc[0, "name"]
    exported_description = frame.loc[0, "plainDescription"]

    assert exported_name == "N" * 79
    assert exported_description == "A" * 15999


def test_wix_export_prefers_typed_fields_when_present() -> None:
    product = Product(
        platform="shopify",
        id="900",
        title="Typed Set",
        description="Typed description",
        price={"amount": 999.99, "currency": "USD"},
        images=["https://cdn.example.com/legacy-wrong-product.jpg"],
        options={"Legacy": ["Wrong"]},
        variants=[
            Variant(
                id="v1",
                sku="TS-BLUE",
                options={"Legacy": "Wrong"},
                price_amount=111.11,
                inventory_quantity=999,
            )
        ],
        raw={},
    )
    product.options_v2 = [OptionDef(name="Color", values=["Blue"])]
    product.media_v2 = [
        Media(url="https://cdn.example.com/typed-product-1.jpg", is_primary=True),
        Media(url="https://cdn.example.com/typed-product-2.jpg"),
    ]

    variant = product.variants[0]
    variant.price_v2 = Price(current=Money(amount=Decimal("12.34"), currency="USD"))
    variant.option_values_v2 = [OptionValue(name="Color", value="Blue")]
    variant.inventory_v2 = Inventory(track_quantity=True, quantity=7, available=True)

    csv_text, _ = product_to_wix_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WIX_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "fieldType"] == "PRODUCT"
    assert frame.loc[0, "price"] == "12.34"
    assert frame.loc[0, "inventory"] == "7"
    assert frame.loc[0, "productOptionName1"] == "Color"
    assert frame.loc[0, "productOptionChoices1"] == "Blue"
    assert frame.loc[0, "media"] == "https://cdn.example.com/typed-product-1.jpg"
    assert frame.loc[1, "fieldType"] == "VARIANT"
    assert frame.loc[1, "price"] == "12.34"
    assert frame.loc[1, "inventory"] == "7"
    assert frame.loc[1, "productOptionChoices1"] == "Blue"
    assert frame.loc[2, "fieldType"] == "MEDIA"
    assert frame.loc[2, "media"] == "https://cdn.example.com/typed-product-2.jpg"
