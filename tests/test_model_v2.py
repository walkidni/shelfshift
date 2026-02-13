from decimal import Decimal

from app.models import (
    Media,
    Money,
    Price,
    Product,
    Variant,
    Weight,
    format_decimal,
    normalize_currency,
    parse_decimal_money,
    resolve_all_image_urls,
    resolve_current_money,
    resolve_primary_image_url,
)


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
        price={"amount": 12.34, "currency": "USD"},
    )
    variant = Variant(id="v-1")

    assert product.price_v2 is None
    assert product.media_v2 == []
    assert product.categories_v2 == []
    assert product.identifiers == {}
    assert product.provenance == {}

    assert variant.price_v2 is None
    assert variant.media_v2 == []
    assert variant.identifiers == {}


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

    variant.price_amount = None
    variant.currency = None
    resolved = resolve_current_money(product, variant)
    assert resolved == Money(amount=Decimal("49"), currency="USD")

    variant.price_v2 = Price(current=Money(amount=Decimal("15.25"), currency="eur"))
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
    product.media_v2 = [
        Media(url="https://cdn.example.com/p-1.jpg", is_primary=False),
        Media(url="https://cdn.example.com/p-hero.jpg", is_primary=True),
        Media(url="https://cdn.example.com/p-2.jpg"),
    ]
    variant = Variant(
        id="v-1",
        sku="SKU-1",
        image="https://cdn.example.com/v-fallback.jpg",
        media_v2=[
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
