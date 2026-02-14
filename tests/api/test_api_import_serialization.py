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
    SourceRef,
    Variant,
    Weight,
    serialize_product_for_api,
)


def _assert_no_v2_keys(value) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert "_v2" not in key
            _assert_no_v2_keys(child)
        return
    if isinstance(value, list):
        for child in value:
            _assert_no_v2_keys(child)


def test_serialize_product_for_api_emits_canonical_payload() -> None:
    variant = Variant(
        id="variant-1",
        sku="SKU-1",
        title="Black / M",
        option_values=[
            OptionValue(name="Color", value="Black"),
            OptionValue(name="Size", value="M"),
        ],
        price=Price(current=Money(amount=Decimal("18.5000"), currency="eur")),
        inventory=Inventory(track_quantity=True, quantity=8, allow_backorder=False),
        weight=Weight(value=Decimal("250"), unit="g"),
        media=[Media(url="https://cdn.example.com/typed-variant.jpg", type="image", is_primary=True)],
        identifiers=Identifiers(values={"gtin": "4006381333931"}),
    )

    product = Product(
        source=SourceRef(
            platform="shopify",
            id="prod-1",
            slug="jet-mug",
            url="https://store.example/products/jet-mug",
        ),
        title="Jet Mug",
        description="<p>Desc</p>",
        seo=Seo(title="Typed SEO Title", description="Typed SEO Description"),
        brand="Acme",
        vendor="Acme",
        taxonomy=CategorySet(paths=[["Kitchen", "Drinkware", "Mugs"]], primary=["Kitchen", "Drinkware", "Mugs"]),
        tags=["coffee", "mug"],
        options=[
            OptionDef(name="Color", values=["Black", "White"]),
            OptionDef(name="Size", values=["S", "M"]),
        ],
        variants=[variant],
        price=Price(
            current=Money(amount=Decimal("19.9900"), currency="usd"),
            compare_at=Money(amount=Decimal("29.00"), currency="usd"),
        ),
        weight=Weight(value=Decimal("1100"), unit="g"),
        media=[
            Media(url="https://cdn.example.com/typed-product.jpg", type="image", alt="Primary", position=1, is_primary=True),
            Media(url="https://cdn.example.com/video.mp4", type="video"),
        ],
        identifiers=Identifiers(values={"barcode": "1234567890123"}),
        provenance={"trace_id": "trace-1"},
    )

    payload = serialize_product_for_api(product, include_raw=False)

    _assert_no_v2_keys(payload)
    assert payload["source"] == {
        "platform": "shopify",
        "id": "prod-1",
        "slug": "jet-mug",
        "url": "https://store.example/products/jet-mug",
    }
    assert payload["price"]["current"]["amount"] == "19.99"
    assert payload["price"]["current"]["currency"] == "USD"
    assert payload["price"]["compare_at"]["amount"] == "29"
    assert payload["seo"] == {"title": "Typed SEO Title", "description": "Typed SEO Description"}
    assert payload["taxonomy"] == {
        "paths": [["Kitchen", "Drinkware", "Mugs"]],
        "primary": ["Kitchen", "Drinkware", "Mugs"],
    }
    assert payload["options"] == [
        {"name": "Color", "values": ["Black", "White"]},
        {"name": "Size", "values": ["S", "M"]},
    ]
    assert payload["variants"][0]["price"] == {
        "current": {"amount": "18.5", "currency": "EUR"},
        "compare_at": None,
        "cost": None,
        "min_price": None,
        "max_price": None,
    }
    assert payload["variants"][0]["option_values"] == [
        {"name": "Color", "value": "Black"},
        {"name": "Size", "value": "M"},
    ]
    assert payload["variants"][0]["inventory"] == {
        "track_quantity": True,
        "quantity": 8,
        "available": None,
        "allow_backorder": False,
    }
    assert "available" not in payload["variants"][0]
    assert payload["weight"] == {"value": "1100", "unit": "g"}
    assert payload["variants"][0]["weight"] == {"value": "250", "unit": "g"}
    assert payload["identifiers"] == {"values": {"barcode": "1234567890123"}}
    assert payload["provenance"] == {"trace_id": "trace-1"}
    assert "raw" not in payload


def test_serialize_product_for_api_respects_include_raw() -> None:
    product = Product(
        source=SourceRef(platform="shopify", id="1", slug="legacy-product"),
        title="Legacy Product",
        description="desc",
        price=Price(current=Money(amount=Decimal("5.0"), currency="USD")),
        variants=[Variant(id="v1", raw={"variant": True})],
        raw={"upstream": True},
    )

    without_raw = serialize_product_for_api(product, include_raw=False)
    with_raw = serialize_product_for_api(product, include_raw=True)

    assert "raw" not in without_raw
    assert "raw" not in without_raw["variants"][0]
    assert with_raw["raw"] == {"upstream": True}
    assert with_raw["variants"][0]["raw"] == {"variant": True}
