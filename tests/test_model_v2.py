from decimal import Decimal

from app.models import Media, Money, Price, Weight, format_decimal, normalize_currency, parse_decimal_money


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
