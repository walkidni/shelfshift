from decimal import Decimal

from app.models import Media, Money, Price, Weight, format_decimal, normalize_currency, parse_decimal_money


def test_models_module_exports_shared_types_and_formatting_helpers() -> None:
    money = Money(amount=Decimal("1.23"), currency="USD")
    price = Price(current=money)
    weight = Weight(value=Decimal("100"), unit="g")
    media = Media(url="https://cdn.example.com/img.jpg")

    assert price.current == money
    assert weight.unit == "g"
    assert media.type == "image"
    assert parse_decimal_money("1.23") == Decimal("1.23")
    assert normalize_currency(" usd ") == "USD"
    assert format_decimal(Decimal("1.2300")) == "1.23"
