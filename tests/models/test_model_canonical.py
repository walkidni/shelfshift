from decimal import Decimal

import pytest

from typeshift.core.canonical import Money, Price, Product, SourceRef, Variant, Weight, resolve_current_money


def test_product_and_variant_support_canonical_fields_only() -> None:
    product = Product(
        source=SourceRef(platform="shopify", id="p-1", slug="demo"),
        title="Demo",
        price=Price(current=Money(amount=Decimal("49.0"), currency="usd")),
    )
    variant = Variant(
        id="v-1",
        price=Price(current=Money(amount=Decimal("19.99"), currency="usd")),
    )

    resolved = resolve_current_money(product, variant)
    assert resolved == Money(amount=Decimal("19.99"), currency="USD")


def test_legacy_constructor_kwargs_are_rejected() -> None:
    with pytest.raises(TypeError):
        Product(platform="shopify", id="p-1", title="Demo")

    with pytest.raises(TypeError):
        Variant(id="v-1", options={"Color": "Black"})


def test_weight_is_typed_and_serialized_as_object() -> None:
    product = Product(
        source=SourceRef(platform="aliexpress", id="p-1", slug="demo"),
        weight=1100.0,
        variants=[Variant(id="v-1", weight=Weight(value=Decimal("250"), unit="g"))],
    )

    payload = product.to_dict(include_raw=False)

    assert payload["weight"] == {"value": "1100", "unit": "g"}
    assert payload["variants"][0]["weight"] == {"value": "250", "unit": "g"}


def test_variant_inventory_serialization_includes_available() -> None:
    variant = Variant(
        id="v-1",
        inventory={"track_quantity": True, "quantity": 4, "available": True, "allow_backorder": False},
    )

    payload = variant.to_dict(include_raw=False)

    assert "available" not in payload
    assert payload["inventory"] == {
        "track_quantity": True,
        "quantity": 4,
        "available": True,
        "allow_backorder": False,
    }
