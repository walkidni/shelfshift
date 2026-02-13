from decimal import Decimal

from app.models import Media, Money, Price, ProductResult, Variant, Weight, format_decimal, normalize_currency, parse_decimal_money


def test_models_module_exports_v1_and_v2_types() -> None:
    product = ProductResult(
        platform="shopify",
        id="1",
        title="Demo",
        description="Demo",
        price={"amount": 1.0, "currency": "USD"},
    )
    variant = Variant(id="v1", price_amount=1.0)
    money = Money(amount=Decimal("1.23"), currency="USD")
    price = Price(current=money)
    weight = Weight(value=Decimal("100"), unit="g")
    media = Media(url="https://cdn.example.com/img.jpg")

    assert product.platform == "shopify"
    assert variant.id == "v1"
    assert price.current == money
    assert weight.unit == "g"
    assert media.type == "image"
    assert parse_decimal_money("1.23") == Decimal("1.23")
    assert normalize_currency(" usd ") == "USD"
    assert format_decimal(Decimal("1.2300")) == "1.23"
