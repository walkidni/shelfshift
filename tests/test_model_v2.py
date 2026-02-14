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
    Seo,
    SourceRef,
    Weight,
    format_decimal,
    normalize_currency,
    parse_decimal_money,
    resolve_all_image_urls,
    resolve_current_money,
    resolve_option_defs,
    resolve_primary_image_url,
    resolve_taxonomy_paths,
    resolve_variant_option_values,
)
from tests._model_builders import Product, Variant


def test_parse_decimal_money_uses_string_conversion_for_floats() -> None:
    parsed = parse_decimal_money(12.34)
    assert parsed == Decimal("12.34")


def test_parse_decimal_money_parses_currency_symbols_and_commas() -> None:
    parsed = parse_decimal_money("$1,234.50 USD")
    assert parsed == Decimal("1234.50")


def test_parse_decimal_money_rejects_empty_or_non_finite_values() -> None:
    assert parse_decimal_money("") is None
    assert parse_decimal_money(float("nan")) is None
    assert parse_decimal_money(float("inf")) is None


def test_normalize_currency_uppercases_and_drops_empty_values() -> None:
    assert normalize_currency(" usd ") == "USD"
    assert normalize_currency("") is None
    assert normalize_currency(None) is None


def test_format_decimal_strips_trailing_zeros() -> None:
    assert format_decimal(Decimal("12.3400")) == "12.34"
    assert format_decimal(Decimal("10.000")) == "10"
    assert format_decimal(None) == ""


def test_v2_dataclasses_have_safe_defaults() -> None:
    price = Price()
    assert price.current == Money()
    assert price.compare_at is None
    assert price.cost is None
    assert price.min_price is None
    assert price.max_price is None

    media_a = Media(url="https://cdn.example.com/1.jpg")
    media_b = Media(url="https://cdn.example.com/2.jpg")
    media_a.variant_skus.append("SKU-1")
    assert media_b.variant_skus == []

    weight = Weight()
    assert weight.value is None
    assert weight.unit == "g"


def test_product_and_variant_phase2_fields_have_safe_defaults() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
    )
    variant = Variant(id="v-1")

    assert product.price is None
    assert product.media == []
    assert product.identifiers.values == {}
    assert product.options == []
    assert product.seo is not None
    assert product.source is not None
    assert product.taxonomy is not None
    assert product.provenance == {}

    assert variant.price is None
    assert variant.media == []
    assert variant.identifiers.values == {}
    assert variant.option_values == []
    assert variant.inventory is not None


def test_resolve_current_money_prefers_v2_then_v1_variant_then_v1_product() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "usd"},
    )
    variant = Variant(id="v-1", price_amount=19.99, currency="usd")

    resolved = resolve_current_money(product, variant)
    assert resolved == Money(amount=Decimal("19.99"), currency="USD")

    variant.price = None
    resolved = resolve_current_money(product, variant)
    assert resolved == Money(amount=Decimal("49"), currency="USD")

    variant.price = Price(current=Money(amount=Decimal("15.25"), currency="eur"))
    resolved = resolve_current_money(product, variant)
    assert resolved == Money(amount=Decimal("15.25"), currency="EUR")


def test_resolve_primary_image_url_prefers_variant_then_product_and_dedupes_all_urls() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "USD"},
        images=["https://cdn.example.com/p-1.jpg", "https://cdn.example.com/p-2.jpg"],
    )
    product.media = [
        Media(url="https://cdn.example.com/p-1.jpg", is_primary=False),
        Media(url="https://cdn.example.com/p-hero.jpg", is_primary=True),
        Media(url="https://cdn.example.com/p-2.jpg"),
    ]
    variant = Variant(
        id="v-1",
        sku="SKU-1",
        image="https://cdn.example.com/v-fallback.jpg",
        media=[
            Media(url="https://cdn.example.com/v-2.jpg"),
            Media(url="https://cdn.example.com/v-primary.jpg", is_primary=True),
        ],
    )

    primary = resolve_primary_image_url(product, variant)
    assert primary == "https://cdn.example.com/v-primary.jpg"

    all_urls = resolve_all_image_urls(product)
    assert all_urls == [
        "https://cdn.example.com/p-1.jpg",
        "https://cdn.example.com/p-hero.jpg",
        "https://cdn.example.com/p-2.jpg",
    ]


def test_phase1_structured_dataclasses_have_safe_defaults() -> None:
    option_def_a = OptionDef(name="Color")
    option_def_b = OptionDef(name="Size")
    option_def_a.values.append("Black")
    assert option_def_b.values == []

    option_value = OptionValue(name="Color", value="Black")
    assert option_value.name == "Color"
    assert option_value.value == "Black"

    inventory = Inventory()
    assert inventory.track_quantity is None
    assert inventory.quantity is None
    assert inventory.available is None
    assert inventory.allow_backorder is None

    seo = Seo()
    assert seo.title is None
    assert seo.description is None

    source = SourceRef(platform="shopify")
    assert source.platform == "shopify"
    assert source.id is None
    assert source.slug is None
    assert source.url is None

    category_set_a = CategorySet()
    category_set_b = CategorySet()
    category_set_a.paths.append(["Men", "Shoes"])
    assert category_set_b.paths == []
    assert category_set_a.primary is None

    identifiers_a = Identifiers()
    identifiers_b = Identifiers()
    identifiers_a.values["gtin"] = "1234567890123"
    assert identifiers_b.values == {}


def test_resolve_option_defs_prefers_typed_then_falls_back_to_legacy_sources() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "USD"},
        options={"Color": ["Black"]},
        variants=[Variant(id="v-1", options={"Color": "White", "Material": "Cotton"})],
    )
    product.options = [
        OptionDef(name="Size", values=["M", "L"]),
        OptionDef(name="Color", values=["Blue"]),
    ]

    resolved = resolve_option_defs(product)
    assert resolved == [
        OptionDef(name="Size", values=["M", "L"]),
        OptionDef(name="Color", values=["Blue"]),
    ]

    product.options = []
    resolved = resolve_option_defs(product)
    assert resolved == []


def test_resolve_variant_option_values_prefers_typed_then_falls_back_to_legacy_options() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "USD"},
        options={"Color": ["Black", "White"], "Size": ["M", "L"]},
    )
    variant = Variant(id="v-1", options={"Color": "White", "Size": "L"})
    variant.option_values = [OptionValue(name="Material", value="Cotton")]

    resolved = resolve_variant_option_values(product, variant)
    assert resolved == [OptionValue(name="Material", value="Cotton")]

    variant.option_values = []
    resolved = resolve_variant_option_values(product, variant)
    assert resolved == []


def test_resolve_taxonomy_paths_prefers_typed_when_present() -> None:
    product = Product(
        platform="shopify",
        id="p-1",
        title="Demo",
        description="Demo",
        price={"amount": 49.0, "currency": "USD"},
        category="Legacy Category",
    )
    product.taxonomy = CategorySet(paths=[["Men", "Shoes"], ["Sale"]], primary=["Men", "Shoes"])

    resolved = resolve_taxonomy_paths(product)
    assert resolved == [["Men", "Shoes"], ["Sale"]]

    product.taxonomy = CategorySet(paths=[], primary=None)
    resolved = resolve_taxonomy_paths(product)
    assert resolved == []
