from app.services.exporters import product_to_wix_csv
from app.services.exporters.wix_csv import WIX_COLUMNS
from app.services.importer import ProductResult, Variant
from tests._csv_helpers import read_frame


def test_wix_export_maps_product_and_variant_rows() -> None:
    product = ProductResult(
        platform="shopify",
        id="101",
        title="Guava Glow Set",
        description="Glow kit",
        price={"amount": 29.99, "currency": "USD"},
        images=["https://example.com/img1.jpg"],
        options={"Size": ["Small", "Medium"]},
        variants=[
            Variant(
                id="v1",
                sku="GG-S",
                options={"Size": "Small"},
                price_amount=29.99,
                inventory_quantity=10,
            ),
            Variant(
                id="v2",
                sku="GG-M",
                options={"Size": "Medium"},
                price_amount=29.99,
                inventory_quantity=8,
            ),
        ],
        slug="guava-glow-set",
        raw={},
    )

    csv_text, filename = product_to_wix_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert filename == "wix-20260208T000000Z.csv"
    assert list(frame.columns) == WIX_COLUMNS
    assert len(frame) == 3

    assert frame.loc[0, "handle"] == "guava-glow-set"
    assert frame.loc[0, "fieldType"] == "PRODUCT"
    assert frame.loc[0, "name"] == "Guava Glow Set"
    assert frame.loc[0, "visible"] == "TRUE"
    assert frame.loc[0, "price"] == "29.99"
    assert frame.loc[0, "productOptionName[1]"] == "Size"
    assert frame.loc[0, "productOptionType[1]"] == "TEXT_CHOICES"
    assert frame.loc[0, "productOptionChoices[1]"] == "Small;Medium"
    assert frame.loc[0, "mediaUrl"] == "https://example.com/img1.jpg"

    assert frame.loc[1, "fieldType"] == "VARIANT"
    assert frame.loc[1, "sku"] == "GG-S"
    assert frame.loc[1, "inventory"] == "10"
    assert frame.loc[1, "productOptionChoices[1]"] == "Small"

    assert frame.loc[2, "fieldType"] == "VARIANT"
    assert frame.loc[2, "sku"] == "GG-M"
    assert frame.loc[2, "inventory"] == "8"
    assert frame.loc[2, "productOptionChoices[1]"] == "Medium"


def test_wix_export_synthesizes_option_column_when_variants_have_no_options() -> None:
    product = ProductResult(
        platform="aliexpress",
        id="1005008518647948",
        title="Therapy Mask",
        description="Mask",
        price={"amount": 50.4, "currency": "USD"},
        images=[],
        variants=[
            Variant(id="v1", sku="AE-1", title="Only Face mask", price_amount=50.4),
            Variant(id="v2", sku="AE-2", title="Only Neck White", price_amount=60.4),
        ],
        raw={},
    )

    csv_text, _ = product_to_wix_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WIX_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "fieldType"] == "PRODUCT"
    assert frame.loc[0, "visible"] == "FALSE"
    assert frame.loc[0, "productOptionName[1]"] == "Option"
    assert frame.loc[0, "productOptionChoices[1]"] == "Only Face mask;Only Neck White"
    assert frame.loc[1, "productOptionChoices[1]"] == "Only Face mask"
    assert frame.loc[2, "productOptionChoices[1]"] == "Only Neck White"
