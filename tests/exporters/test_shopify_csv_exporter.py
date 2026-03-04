from decimal import Decimal

from tests.helpers._csv_helpers import read_frame
from tests.helpers._model_builders import Product, Variant

from shelfshift.core.canonical import (
    CategorySet,
    Inventory,
    Media,
    Money,
    OptionDef,
    OptionValue,
    Price,
)
from shelfshift.core.exporters import product_to_shopify_csv
from shelfshift.core.exporters.platforms.shopify import SHOPIFY_COLUMNS, SHOPIFY_DEFAULT_IMAGE_URL


def test_single_variant_uses_default_title_option() -> None:
    product = Product(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[],
    )

    csv_text, filename = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert filename == "shopify-20260208T000000Z.csv"
    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Option1 name"] == "Title"
    assert frame.loc[0, "Option1 value"] == "Default Title"
    assert frame.loc[0, "Published on online store"] == "FALSE"
    assert frame.loc[0, "Status"] == "Draft"
    assert frame.loc[0, "Variant image URL"] == ""


def test_export_uses_new_shopify_template_headers_and_core_fields() -> None:
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
                inventory_quantity=4,
                weight=250,
                image="https://cdn.example.com/mug-v.jpg",
            )
        ],
    )

    csv_text, _ = product_to_shopify_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert "URL handle" in frame.columns
    assert "Description" in frame.columns
    assert "SKU" in frame.columns
    assert "Price" in frame.columns
    assert "Product image URL" in frame.columns
    assert "Variant image URL" in frame.columns
    assert "Handle" not in frame.columns
    assert "Body (HTML)" not in frame.columns
    assert "Variant SKU" not in frame.columns
    assert "Variant Price" not in frame.columns

    assert frame.loc[0, "URL handle"] == "demo-mug"
    assert frame.loc[0, "Description"] == "Demo description"
    assert frame.loc[0, "SKU"] == "AMZ-MUG-001"
    assert frame.loc[0, "Price"] == "12"
    assert frame.loc[0, "Product image URL"] == "https://cdn.example.com/mug.jpg"
    assert frame.loc[0, "Variant image URL"] == "https://cdn.example.com/mug-v.jpg"


def test_multi_variant_maps_two_options() -> None:
    product = Product(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="Soft cotton tee",
        price={"amount": 19.99, "currency": "USD"},
        images=[],
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
                image="https://cdn.example.com/tee-white-l.jpg",
            ),
        ],
    )

    csv_text, _ = product_to_shopify_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Option1 name"] == "Color"
    assert frame.loc[0, "Option1 value"] == "Black"
    assert frame.loc[0, "Option2 name"] == "Size"
    assert frame.loc[0, "Option2 value"] == "M"
    assert frame.loc[1, "Option1 value"] == "White"
    assert frame.loc[1, "Option2 value"] == "L"
    assert frame.loc[0, "Inventory tracker"] == "shopify"
    assert frame.loc[0, "Inventory quantity"] == "4"
    assert frame.loc[0, "Continue selling when out of stock"] == "FALSE"
    assert frame.loc[1, "Continue selling when out of stock"] == "FALSE"
    assert frame.loc[1, "Title"] == ""
    assert frame.loc[0, "Variant image URL"] == "https://cdn.example.com/tee-black-m.jpg"
    assert frame.loc[1, "Variant image URL"] == "https://cdn.example.com/tee-white-l.jpg"
    assert frame.loc[0, "Published on online store"] == "TRUE"
    assert frame.loc[0, "Status"] == "Active"


def test_multiple_images_create_extra_rows() -> None:
    product = Product(
        platform="shopify",
        id="202",
        title="Poster",
        description="Wall art",
        price={"amount": 10.0, "currency": "USD"},
        images=[
            "https://cdn.example.com/poster-1.jpg",
            "https://cdn.example.com/poster-2.jpg",
            "https://cdn.example.com/poster-3.jpg",
        ],
        variants=[
            Variant(
                id="pv1",
                sku="POSTER-1",
                price_amount=10.0,
                image="https://cdn.example.com/poster-variant.jpg",
            )
        ],
    )

    csv_text, _ = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "Product image URL"] == "https://cdn.example.com/poster-1.jpg"
    assert frame.loc[0, "Image position"] == "1"
    assert frame.loc[1, "Product image URL"] == "https://cdn.example.com/poster-2.jpg"
    assert frame.loc[1, "Image position"] == "2"
    assert frame.loc[1, "Title"] == ""
    assert frame.loc[2, "Product image URL"] == "https://cdn.example.com/poster-3.jpg"
    assert frame.loc[2, "Image position"] == "3"
    assert frame.loc[0, "Variant image URL"] == "https://cdn.example.com/poster-variant.jpg"
    assert frame.loc[1, "Variant image URL"] == ""
    assert frame.loc[2, "Variant image URL"] == ""
    assert frame.loc[1, "SKU"] == ""
    assert frame.loc[2, "SKU"] == ""


def test_body_html_round_trips_quotes_commas_newlines() -> None:
    body = 'He said "hello", then left.\nSecond line, still in body.'
    product = Product(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description=body,
        price={"amount": 12.0, "currency": "USD"},
        images=[],
    )

    csv_text, _ = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert frame.loc[0, "Description"] == body


def test_non_shopify_source_generates_handle_and_blank_inventory() -> None:
    product = Product(
        platform="amazon",
        id="B00ABC1234",
        title="Fancy Lamp 2.0!",
        description="Desk lamp",
        price={"amount": 49.5, "currency": "USD"},
        images=[],
        variants=[Variant(id="B00ABC1234", price_amount=49.5, inventory_quantity=None)],
    )

    csv_text, filename = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert filename == "shopify-20260208T000000Z.csv"
    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert frame.loc[0, "URL handle"] == "fancy-lamp-2-0"
    assert frame.loc[0, "Variant image URL"] == ""
    assert frame.loc[0, "Inventory tracker"] == ""
    assert frame.loc[0, "Inventory quantity"] == ""
    assert frame.loc[0, "Continue selling when out of stock"] == "FALSE"


def test_shopify_export_allows_weight_unit_override_without_changing_grams() -> None:
    product = Product(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="Soft cotton tee",
        price={"amount": 19.99, "currency": "USD"},
        images=[],
        variants=[
            Variant(
                id="v1",
                sku="TEE-BLK-M",
                price_amount=19.99,
                weight=250,
            )
        ],
    )

    csv_text, _ = product_to_shopify_csv(product, publish=True, weight_unit="lb")
    frame = read_frame(csv_text)

    assert frame.loc[0, "Weight value (grams)"] == "250"
    assert frame.loc[0, "Weight unit for display"] == "lb"


def test_exporter_keeps_namespaced_aliexpress_sku_as_string() -> None:
    product = Product(
        platform="aliexpress",
        id="1005008518647948",
        title="Therapy Mask",
        description="Mask description",
        price={"amount": 50.4, "currency": "USD"},
        images=[],
        variants=[
            Variant(
                id="12000055918704599",
                sku="AE:1005008518647948:12000055918704599",
                options={"Color": "Only Face mask"},
                price_amount=50.4,
            )
        ],
    )

    csv_text, _ = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert frame.loc[0, "SKU"] == "AE:1005008518647948:12000055918704599"
    assert frame.loc[0, "Variant image URL"] == ""


def test_invalid_image_urls_fallback_to_default_shopify_image() -> None:
    product = Product(
        platform="squarespace",
        id="4280546",
        title="Large Boxy Quilt Pouch (R)",
        description="Pouch description",
        price={"amount": 35.0, "currency": "USD"},
        images=[
            "https://static1.squarespace.com/static/680ed8af/680ed8b0/693f5bcc/1765764069386/",
            "https://static1.squarespace.com/static/680ed8af/680ed8b0/693f5bcc/1765764069387/",
            "https://cdn.example.com/large-boxy-pouch.jpg",
        ],
        variants=[
            Variant(
                id="v1",
                sku="SQ4280546",
                price_amount=35.0,
                image="https://static1.squarespace.com/static/680ed8af/680ed8b0/693f5bcc/1765764069388/",
            )
        ],
        slug="large-boxy-quilt-pouch-r",
    )

    csv_text, _ = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Product image URL"] == SHOPIFY_DEFAULT_IMAGE_URL
    assert frame.loc[1, "Product image URL"] == "https://cdn.example.com/large-boxy-pouch.jpg"
    assert frame.loc[0, "Variant image URL"] == SHOPIFY_DEFAULT_IMAGE_URL


def test_typed_fields_override_legacy_values_when_present() -> None:
    product = Product(
        platform="shopify",
        id="900",
        title="Typed Hoodie",
        description="Typed description",
        price={"amount": 99.99, "currency": "USD"},
        images=["https://cdn.example.com/legacy-product.jpg"],
        options={"LegacyOption": ["LegacyValue"]},
        category="Legacy Category",
        variants=[
            Variant(
                id="v-typed-1",
                sku="LEGACY-SKU-1",
                options={"LegacyOption": "LegacyValue"},
                price_amount=77.77,
                inventory_quantity=None,
                image="https://cdn.example.com/legacy-variant.jpg",
            )
        ],
    )
    product.price = Price(current=Money(amount=Decimal("55.5"), currency="eur"))
    product.media = [
        Media(url="https://cdn.example.com/typed-main.jpg", is_primary=True),
        Media(url="https://cdn.example.com/typed-gallery.jpg"),
    ]
    product.options = [OptionDef(name="Color", values=["Blue"])]
    product.taxonomy = CategorySet(paths=[["Men", "Outerwear"]], primary=["Men", "Outerwear"])

    variant = product.variants[0]
    variant.price = Price(current=Money(amount=Decimal("12.34"), currency="cad"))
    variant.media = [Media(url="https://cdn.example.com/typed-variant.jpg", is_primary=True)]
    variant.option_values = [OptionValue(name="Color", value="Blue")]
    variant.inventory = Inventory(track_quantity=True, quantity=7, available=True)

    csv_text, _ = product_to_shopify_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Option1 name"] == "Color"
    assert frame.loc[0, "Option1 value"] == "Blue"
    assert frame.loc[0, "Type"] == "Men > Outerwear"
    assert frame.loc[0, "Price"] == "12.34"
    assert frame.loc[0, "Inventory tracker"] == "shopify"
    assert frame.loc[0, "Inventory quantity"] == "7"
    assert frame.loc[0, "Product image URL"] == "https://cdn.example.com/typed-main.jpg"
    assert frame.loc[1, "Product image URL"] == "https://cdn.example.com/typed-gallery.jpg"
    assert frame.loc[0, "Variant image URL"] == "https://cdn.example.com/typed-variant.jpg"
