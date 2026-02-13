from decimal import Decimal

from app.models import (
    CategorySet,
    Identifiers,
    Inventory,
    Media,
    Money,
    OptionDef,
    OptionValue,
    Price,
    Product,
    Seo,
    Variant,
)
from app.services.exporters import utils


def test_resolve_price_helpers_prefer_typed_then_variant_then_product_legacy() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "usd"},
    )
    variant = Variant(id="v-1", price_amount=19.99, currency="usd")

    assert utils.resolve_price_amount(product, variant) == 19.99
    assert utils.resolve_price_currency(product, variant) == "USD"

    variant.price_v2 = Price(current=Money(amount=Decimal("15.25"), currency="eur"))
    assert utils.resolve_price_amount(product, variant) == 15.25
    assert utils.resolve_price_currency(product, variant) == "EUR"

    variant.price_v2 = None
    variant.price_amount = None
    variant.currency = None
    assert utils.resolve_price_amount(product, variant) == 49.0
    assert utils.resolve_price_currency(product, variant) == "USD"


def test_resolve_media_helpers_prefer_typed_then_fallback_legacy() -> None:
    variant = Variant(
        id="v-1",
        image="https://cdn.example.com/v-fallback.jpg",
    )
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "USD"},
        images=["https://cdn.example.com/p-1.jpg", "https://cdn.example.com/p-2.jpg"],
        variants=[variant],
    )
    product.media_v2 = [
        Media(url="https://cdn.example.com/p-hero.jpg", is_primary=True),
        Media(url="https://cdn.example.com/p-1.jpg"),
    ]
    variant.media_v2 = [
        Media(url="https://cdn.example.com/v-2.jpg"),
        Media(url="https://cdn.example.com/v-primary.jpg", is_primary=True),
    ]

    assert (
        utils.resolve_primary_image_url(product, variant)
        == "https://cdn.example.com/v-primary.jpg"
    )

    variant.media_v2 = []
    assert utils.resolve_primary_image_url(product, variant) == "https://cdn.example.com/v-fallback.jpg"
    assert utils.resolve_all_image_urls(product) == [
        "https://cdn.example.com/p-hero.jpg",
        "https://cdn.example.com/p-1.jpg",
        "https://cdn.example.com/p-2.jpg",
        "https://cdn.example.com/v-fallback.jpg",
    ]


def test_resolve_option_helpers_prefer_typed_then_legacy() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "USD"},
        options={"Color": ["Black", "White"]},
        variants=[Variant(id="v-1", options={"Color": "White", "Size": "M"})],
    )
    variant = product.variants[0]

    product.options_v2 = [
        OptionDef(name="Size", values=["M", "L"]),
        OptionDef(name="Color", values=["Blue"]),
    ]
    variant.option_values_v2 = [OptionValue(name="Material", value="Cotton")]

    assert utils.resolve_option_defs(product) == [
        OptionDef(name="Size", values=["M", "L"]),
        OptionDef(name="Color", values=["Blue"]),
    ]
    assert utils.resolve_variant_option_map(product, variant) == {"Material": "Cotton"}

    product.options_v2 = []
    variant.option_values_v2 = []
    assert utils.resolve_option_defs(product) == [
        OptionDef(name="Color", values=["Black", "White"]),
        OptionDef(name="Size", values=["M"]),
    ]
    assert utils.resolve_variant_option_map(product, variant) == {"Color": "White", "Size": "M"}


def test_resolve_taxonomy_helpers_prefer_typed_then_categories_then_legacy() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "USD"},
        category="Legacy Category",
    )
    product.categories_v2 = [["Women", "Dresses"]]
    product.taxonomy_v2 = CategorySet(paths=[["Men", "Shoes"], ["Sale"]], primary=["Men", "Shoes"])

    assert utils.resolve_taxonomy_paths(product) == [["Men", "Shoes"], ["Sale"]]
    assert utils.resolve_primary_category(product) == "Men > Shoes"

    product.taxonomy_v2 = None
    assert utils.resolve_taxonomy_paths(product) == [["Women", "Dresses"]]
    assert utils.resolve_primary_category(product) == "Women > Dresses"

    product.categories_v2 = []
    assert utils.resolve_taxonomy_paths(product) == [["Legacy Category"]]
    assert utils.resolve_primary_category(product) == "Legacy Category"


def test_resolve_seo_helpers_prefer_typed_then_legacy() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "USD"},
        meta_title="Legacy Title",
        meta_description="Legacy Description",
    )
    product.seo_v2 = Seo(title="Typed Title", description="Typed Description")

    assert utils.resolve_seo_title(product) == "Typed Title"
    assert utils.resolve_seo_description(product) == "Typed Description"

    product.seo_v2 = None
    assert utils.resolve_seo_title(product) == "Legacy Title"
    assert utils.resolve_seo_description(product) == "Legacy Description"


def test_resolve_inventory_helpers_prefer_typed_then_legacy() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "USD"},
        track_quantity=False,
    )
    variant = Variant(
        id="v-1",
        inventory_quantity=3,
        available=False,
        inventory_v2=Inventory(
            track_quantity=True,
            quantity=7,
            available=True,
            allow_backorder=False,
        ),
    )

    assert utils.resolve_variant_track_quantity(product, variant) is True
    assert utils.resolve_variant_inventory_quantity(variant) == 7
    assert utils.resolve_variant_available(variant) is True
    assert utils.resolve_variant_allow_backorder(variant) is False

    variant.inventory_v2 = None
    assert utils.resolve_variant_track_quantity(product, variant) is True
    assert utils.resolve_variant_inventory_quantity(variant) == 3
    assert utils.resolve_variant_available(variant) is False
    assert utils.resolve_variant_allow_backorder(variant) is None

    variant.inventory_quantity = None
    assert utils.resolve_variant_track_quantity(product, variant) is False
    assert utils.resolve_variant_inventory_quantity(variant) is None


def test_resolve_identifier_helpers_prefer_typed_then_legacy() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "USD"},
        identifiers={"gtin": "legacy-gtin"},
    )
    product.identifiers_v2 = Identifiers(values={"gtin": "typed-gtin", "upc": "12345"})

    variant = Variant(
        id="v-1",
        identifiers={"mpn": "legacy-mpn"},
        identifiers_v2=Identifiers(values={"mpn": "typed-mpn"}),
    )

    assert utils.resolve_identifier_values(product) == {"gtin": "typed-gtin", "upc": "12345"}
    assert utils.resolve_identifier_value(product, "gtin") == "typed-gtin"
    assert utils.resolve_identifier_values(product, variant=variant) == {"mpn": "typed-mpn"}
    assert utils.resolve_identifier_value(product, "mpn", variant=variant) == "typed-mpn"

    product.identifiers_v2 = None
    variant.identifiers_v2 = None
    assert utils.resolve_identifier_values(product) == {"gtin": "legacy-gtin"}
    assert utils.resolve_identifier_values(product, variant=variant) == {"mpn": "legacy-mpn"}
