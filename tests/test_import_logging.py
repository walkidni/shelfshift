from app.models import Product, Variant
from app.services.logging import product_result_to_loggable


def _build_sample_product() -> Product:
    return Product(
        platform="aliexpress",
        id="1005008518647948",
        title="LED Mask",
        description="D" * 500,
        price={"amount": 50.4, "currency": "USD"},
        images=[
            "https://cdn.example.com/image-1.jpg",
            "https://cdn.example.com/image-2.jpg",
        ],
        options={"Color": ["White", "Black"]},
        variants=[
            Variant(
                id="v1",
                sku="SKU-1",
                image="https://cdn.example.com/variant-1.jpg",
                options={"Color": "White"},
                price_amount=50.4,
                currency="USD",
            ),
            Variant(
                id="v2",
                sku="SKU-2",
                image=None,
                options={"Color": "Black"},
                price_amount=60.0,
                currency="USD",
            ),
        ],
        brand="hello face",
        category="mask",
        meta_description="M" * 400,
        slug="aliexpress-led-mask",
        vendor="hello face Official Store",
        raw={"source": "payload"},
    )


def test_product_result_to_loggable_extrahigh_is_full_and_includes_raw() -> None:
    product = _build_sample_product()

    loggable = product_result_to_loggable(product, verbosity="extrahigh")

    assert loggable["id"] == "1005008518647948"
    assert loggable["price"] == {"amount": 50.4, "currency": "USD"}
    assert isinstance(loggable["images"], list)
    assert isinstance(loggable["variants"], list)
    assert loggable["variants"][0]["sku"] == "SKU-1"
    assert loggable["raw"] == {"source": "payload"}
    assert loggable["description"] == "D" * 500
    assert loggable["meta_description"] == "M" * 400


def test_product_result_to_loggable_high_truncates_and_excludes_raw() -> None:
    product = _build_sample_product()

    loggable = product_result_to_loggable(product, verbosity="high")

    assert loggable["id"] == "1005008518647948"
    assert loggable["price"] == {"amount": 50.4, "currency": "USD"}
    assert isinstance(loggable["images"], list)
    assert loggable["variants"][0]["sku"] == "SKU-1"
    assert "raw" not in loggable
    assert loggable["description"].endswith("... [truncated]")
    assert loggable["meta_description"].endswith("... [truncated]")


def test_product_result_to_loggable_medium_omits_ids_and_sku_and_simplifies_variants() -> None:
    product = _build_sample_product()

    loggable = product_result_to_loggable(product, verbosity="medium")

    assert "id" not in loggable
    assert loggable["price"] == "50.4$"
    assert loggable["options"] == {"Color": ["White", "Black"]}
    assert loggable["images"] == {"count": 2}
    assert loggable["variants_count"] == 2
    assert len(loggable["variants"]) == 2
    assert loggable["variants"][0] == {"options": {"Color": "White"}, "price": "50.4$", "has_image": True}
    assert loggable["variants"][1] == {"options": {"Color": "Black"}, "price": "60$", "has_image": False}
    assert "raw" not in loggable


def test_product_result_to_loggable_low_is_compact() -> None:
    product = _build_sample_product()

    loggable = product_result_to_loggable(product, verbosity="low")

    assert set(loggable.keys()) == {"platform", "title", "price", "images", "variants_count", "brand", "category"}
    assert loggable["platform"] == "aliexpress"
    assert loggable["title"] == "LED Mask"
    assert loggable["price"] == "50.4$"
    assert loggable["images"] == {"count": 2}
    assert loggable["variants_count"] == 2
