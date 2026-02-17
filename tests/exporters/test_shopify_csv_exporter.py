from decimal import Decimal

from shelfshift.core.exporters import product_to_shopify_csv
from shelfshift.core.exporters.platforms.shopify import SHOPIFY_COLUMNS, SHOPIFY_DEFAULT_IMAGE_URL
from shelfshift.core.canonical import CategorySet, Inventory, Media, Money, OptionDef, OptionValue, Price
from tests.helpers._model_builders import Product, Variant
from tests.helpers._csv_helpers import read_frame


def test_single_variant_uses_default_title_option() -> None:
    product = Product(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[],
        raw={},
    )

    csv_text, filename = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert filename == "shopify-20260208T000000Z.csv"
    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Option1 Name"] == "Title"
    assert frame.loc[0, "Option1 Value"] == "Default Title"
    assert frame.loc[0, "Published"] == "FALSE"
    assert frame.loc[0, "Status"] == "draft"
    assert frame.loc[0, "Variant Image"] == ""


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
        raw={},
    )

    csv_text, _ = product_to_shopify_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Option1 Name"] == "Color"
    assert frame.loc[0, "Option1 Value"] == "Black"
    assert frame.loc[0, "Option2 Name"] == "Size"
    assert frame.loc[0, "Option2 Value"] == "M"
    assert frame.loc[1, "Option1 Value"] == "White"
    assert frame.loc[1, "Option2 Value"] == "L"
    assert frame.loc[0, "Variant Inventory Tracker"] == "shopify"
    assert frame.loc[0, "Variant Inventory Qty"] == "4"
    assert frame.loc[0, "Variant Inventory Policy"] == "deny"
    assert frame.loc[1, "Variant Inventory Policy"] == "deny"
    assert frame.loc[1, "Title"] == ""
    assert frame.loc[0, "Variant Image"] == "https://cdn.example.com/tee-black-m.jpg"
    assert frame.loc[1, "Variant Image"] == "https://cdn.example.com/tee-white-l.jpg"
    assert frame.loc[0, "Published"] == "TRUE"
    assert frame.loc[0, "Status"] == "active"


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
        raw={},
    )

    csv_text, _ = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "Image Src"] == "https://cdn.example.com/poster-1.jpg"
    assert frame.loc[0, "Image Position"] == "1"
    assert frame.loc[1, "Image Src"] == "https://cdn.example.com/poster-2.jpg"
    assert frame.loc[1, "Image Position"] == "2"
    assert frame.loc[1, "Title"] == ""
    assert frame.loc[2, "Image Src"] == "https://cdn.example.com/poster-3.jpg"
    assert frame.loc[2, "Image Position"] == "3"
    assert frame.loc[0, "Variant Image"] == "https://cdn.example.com/poster-variant.jpg"
    assert frame.loc[1, "Variant Image"] == ""
    assert frame.loc[2, "Variant Image"] == ""
    assert frame.loc[1, "Variant SKU"] == ""
    assert frame.loc[2, "Variant SKU"] == ""


def test_body_html_round_trips_quotes_commas_newlines() -> None:
    body = 'He said "hello", then left.\nSecond line, still in body.'
    product = Product(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description=body,
        price={"amount": 12.0, "currency": "USD"},
        images=[],
        raw={},
    )

    csv_text, _ = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert frame.loc[0, "Body (HTML)"] == body


def test_non_shopify_source_generates_handle_and_blank_inventory() -> None:
    product = Product(
        platform="amazon",
        id="B00ABC1234",
        title="Fancy Lamp 2.0!",
        description="Desk lamp",
        price={"amount": 49.5, "currency": "USD"},
        images=[],
        variants=[Variant(id="B00ABC1234", price_amount=49.5, inventory_quantity=None)],
        raw={},
    )

    csv_text, filename = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert filename == "shopify-20260208T000000Z.csv"
    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert frame.loc[0, "Handle"] == "fancy-lamp-2-0"
    assert frame.loc[0, "Variant Image"] == ""
    assert frame.loc[0, "Variant Inventory Tracker"] == ""
    assert frame.loc[0, "Variant Inventory Qty"] == ""
    assert frame.loc[0, "Variant Inventory Policy"] == "deny"


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
        raw={},
    )

    csv_text, _ = product_to_shopify_csv(product, publish=True, weight_unit="lb")
    frame = read_frame(csv_text)

    assert frame.loc[0, "Variant Grams"] == "250"
    assert frame.loc[0, "Variant Weight Unit"] == "lb"


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
        raw={},
    )

    csv_text, _ = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert frame.loc[0, "Variant SKU"] == "AE:1005008518647948:12000055918704599"
    assert frame.loc[0, "Variant Image"] == ""


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
        raw={},
    )

    csv_text, _ = product_to_shopify_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Image Src"] == SHOPIFY_DEFAULT_IMAGE_URL
    assert frame.loc[1, "Image Src"] == "https://cdn.example.com/large-boxy-pouch.jpg"
    assert frame.loc[0, "Variant Image"] == SHOPIFY_DEFAULT_IMAGE_URL


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
        raw={},
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
    assert frame.loc[0, "Option1 Name"] == "Color"
    assert frame.loc[0, "Option1 Value"] == "Blue"
    assert frame.loc[0, "Type"] == "Men > Outerwear"
    assert frame.loc[0, "Variant Price"] == "12.34"
    assert frame.loc[0, "Variant Inventory Tracker"] == "shopify"
    assert frame.loc[0, "Variant Inventory Qty"] == "7"
    assert frame.loc[0, "Image Src"] == "https://cdn.example.com/typed-main.jpg"
    assert frame.loc[1, "Image Src"] == "https://cdn.example.com/typed-gallery.jpg"
    assert frame.loc[0, "Variant Image"] == "https://cdn.example.com/typed-variant.jpg"
