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


def test_serialize_product_for_api_typed_profile_emits_canonical_typed_payload() -> None:
    variant = Variant(
        id="variant-1",
        sku="SKU-1",
        title="Black / M",
        options={"Color": "LegacyWhite"},
        price_amount=999.0,
        currency="usd",
        image="https://cdn.example.com/legacy-variant.jpg",
        available=False,
        inventory_quantity=0,
    )
    variant.option_values_v2 = [
        OptionValue(name="Color", value="Black"),
        OptionValue(name="Size", value="M"),
    ]
    variant.price_v2 = Price(current=Money(amount=Decimal("18.5000"), currency="eur"))
    variant.media_v2 = [
        Media(url="https://cdn.example.com/typed-variant.jpg", type="image", is_primary=True),
    ]
    variant.inventory_v2 = Inventory(track_quantity=True, quantity=8, available=True, allow_backorder=False)
    variant.identifiers_v2 = Identifiers(values={"gtin": "4006381333931"})

    product = Product(
        platform="shopify",
        id="prod-1",
        title="Jet Mug",
        description="<p>Desc</p>",
        price={"amount": 199.0, "currency": "usd"},
        images=["https://cdn.example.com/legacy-product.jpg"],
        options={"Color": ["LegacyWhite"]},
        variants=[variant],
        category="Legacy Category",
        meta_title="Legacy Meta Title",
        meta_description="Legacy Meta Description",
        slug="jet-mug",
        tags=["coffee", "mug"],
        raw={"upstream": True},
        provenance={"trace_id": "trace-1"},
    )
    product.source_v2 = SourceRef(
        platform="shopify",
        id="prod-1",
        slug="jet-mug",
        url="https://store.example/products/jet-mug",
    )
    product.seo_v2 = Seo(title="Typed SEO Title", description="Typed SEO Description")
    product.taxonomy_v2 = CategorySet(paths=[["Kitchen", "Drinkware", "Mugs"]], primary=["Kitchen", "Drinkware", "Mugs"])
    product.options_v2 = [
        OptionDef(name="Color", values=["Black", "White"]),
        OptionDef(name="Size", values=["S", "M"]),
    ]
    product.price_v2 = Price(
        current=Money(amount=Decimal("19.9900"), currency="usd"),
        compare_at=Money(amount=Decimal("29.00"), currency="usd"),
    )
    product.media_v2 = [
        Media(url="https://cdn.example.com/typed-product.jpg", type="image", alt="Primary", position=1, is_primary=True),
        Media(url="https://cdn.example.com/video.mp4", type="video"),
    ]
    product.identifiers_v2 = Identifiers(values={"barcode": "1234567890123"})

    payload = serialize_product_for_api(product, profile="typed", include_raw=False)

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
    assert payload["media"] == [
        {
            "url": "https://cdn.example.com/typed-product.jpg",
            "type": "image",
            "alt": "Primary",
            "position": 1,
            "is_primary": True,
            "variant_skus": [],
        },
        {
            "url": "https://cdn.example.com/video.mp4",
            "type": "video",
            "alt": None,
            "position": None,
            "is_primary": None,
            "variant_skus": [],
        },
    ]
    assert payload["identifiers"] == {"values": {"barcode": "1234567890123"}}
    assert payload["variants"][0]["price"]["current"]["amount"] == "18.5"
    assert payload["variants"][0]["price"]["current"]["currency"] == "EUR"
    assert payload["variants"][0]["option_values"] == [
        {"name": "Color", "value": "Black"},
        {"name": "Size", "value": "M"},
    ]
    assert payload["variants"][0]["inventory"] == {
        "track_quantity": True,
        "quantity": 8,
        "available": True,
        "allow_backorder": False,
    }
    assert payload["variants"][0]["identifiers"] == {"values": {"gtin": "4006381333931"}}
    assert payload["provenance"] == {"trace_id": "trace-1"}
    assert "raw" not in payload


def test_serialize_product_for_api_typed_profile_falls_back_to_legacy_and_dedupes_media() -> None:
    product = Product(
        platform="woocommerce",
        id="prod-legacy",
        title="Legacy Tee",
        description="Legacy description",
        price={"amount": 12.3400, "currency": "usd"},
        images=[
            "https://cdn.example.com/product-1.jpg",
            "https://cdn.example.com/product-2.jpg",
            "https://cdn.example.com/product-1.jpg",
        ],
        options={"Color": ["Black", "Blue"], "Size": ["M", "L"]},
        variants=[
            Variant(
                id="var-legacy",
                sku="LEG-1",
                options={"Color": "Black", "Size": "M"},
                price_amount=13.5,
                currency="usd",
                image="https://cdn.example.com/variant-1.jpg",
                available=True,
                inventory_quantity=11,
            )
        ],
        category="Tops",
        meta_title="Legacy SEO Title",
        meta_description="Legacy SEO Description",
        slug="legacy-tee",
        tags=["tee"],
        identifiers={"upc": "111222333444"},
        raw={"payload": "raw"},
        track_quantity=False,
    )

    payload = serialize_product_for_api(product, profile="typed", include_raw=True)

    _assert_no_v2_keys(payload)
    assert payload["source"] == {
        "platform": "woocommerce",
        "id": "prod-legacy",
        "slug": "legacy-tee",
        "url": None,
    }
    assert payload["price"] == {
        "current": {"amount": "12.34", "currency": "USD"},
        "compare_at": None,
        "cost": None,
        "min_price": None,
        "max_price": None,
    }
    assert payload["seo"] == {"title": "Legacy SEO Title", "description": "Legacy SEO Description"}
    assert payload["taxonomy"] == {"paths": [["Tops"]], "primary": ["Tops"]}
    assert payload["options"] == [
        {"name": "Color", "values": ["Black", "Blue"]},
        {"name": "Size", "values": ["M", "L"]},
    ]
    assert [item["url"] for item in payload["media"]] == [
        "https://cdn.example.com/product-1.jpg",
        "https://cdn.example.com/product-2.jpg",
        "https://cdn.example.com/variant-1.jpg",
    ]
    assert payload["variants"][0]["price"] == {
        "current": {"amount": "13.5", "currency": "USD"},
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
        "track_quantity": False,
        "quantity": 11,
        "available": True,
        "allow_backorder": None,
    }
    assert payload["identifiers"] == {"values": {"upc": "111222333444"}}
    assert payload["variants"][0]["identifiers"] == {"values": {}}
    assert payload["raw"] == {"payload": "raw"}


def test_serialize_product_for_api_legacy_profile_matches_existing_to_dict() -> None:
    product = Product(
        platform="shopify",
        id="1",
        title="Legacy Product",
        description="desc",
        price={"amount": 5.0, "currency": "USD"},
        images=[],
        variants=[],
        raw={"upstream": True},
    )

    assert serialize_product_for_api(product, profile="legacy", include_raw=False) == product.to_dict(include_raw=False)
    assert serialize_product_for_api(product, profile="legacy", include_raw=True) == product.to_dict(include_raw=True)
