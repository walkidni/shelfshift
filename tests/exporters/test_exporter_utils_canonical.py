from decimal import Decimal

from typeshift.core.canonical import Product, SourceRef, Variant, Weight
from typeshift.core.exporters.shared import utils


def test_resolve_weight_grams_uses_variant_weight_first() -> None:
    product = Product(
        source=SourceRef(platform="shopify", id="p-1"),
        weight=Weight(value=Decimal("1000"), unit="g"),
        variants=[Variant(id="v-1", weight=Weight(value=Decimal("1.25"), unit="kg"))],
    )

    assert utils.resolve_weight_grams(product, product.variants[0]) == 1250.0


def test_resolve_weight_grams_falls_back_to_product_weight() -> None:
    product = Product(
        source=SourceRef(platform="shopify", id="p-1"),
        weight=Weight(value=Decimal("2"), unit="lb"),
        variants=[Variant(id="v-1", weight=None)],
    )

    assert round(utils.resolve_weight_grams(product, product.variants[0]) or 0.0, 6) == 907.18474


def test_resolve_variant_available_prefers_inventory_available() -> None:
    variant = Variant(id="v-1", inventory={"track_quantity": True, "quantity": 3, "available": True})

    assert utils.resolve_variant_available(variant) is True
