from app.services.exporters import product_to_squarespace_csv
from app.services.exporters.squarespace_csv import SQUARESPACE_COLUMNS
from app.services.importer import ProductResult, Variant
from tests._csv_helpers import read_frame


def test_single_variant_maps_visible_and_hosted_images() -> None:
    product = ProductResult(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[
            "https://cdn.example.com/mug-front.jpg",
            "https://cdn.example.com/mug-side.jpg",
        ],
        variants=[
            Variant(
                id="v1",
                sku="AMZ-MUG-001",
                price_amount=12.0,
                inventory_quantity=0,
                weight=250,
            )
        ],
        raw={},
    )

    csv_text, filename = product_to_squarespace_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert filename == "squarespace-20260208T000000Z.csv"
    assert list(frame.columns) == SQUARESPACE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Product Type"] == "physical"
    assert frame.loc[0, "Product Page"] == ""
    assert frame.loc[0, "Product URL"] == ""
    assert frame.loc[0, "SKU"] == "AMZ-MUG-001"
    assert frame.loc[0, "Price"] == "12"
    assert frame.loc[0, "On Sale"] == "FALSE"
    assert frame.loc[0, "Stock"] == "0"
    assert frame.loc[0, "Weight"] == "0.25"
    assert frame.loc[0, "Visible"] == "FALSE"
    assert frame.loc[0, "Hosted Image URLs"] == "https://cdn.example.com/mug-front.jpg\nhttps://cdn.example.com/mug-side.jpg"


def test_multi_variant_uses_first_row_for_product_fields() -> None:
    product = ProductResult(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="Soft cotton tee",
        price={"amount": 19.99, "currency": "USD"},
        images=["https://cdn.example.com/tee.jpg"],
        options={"Size": ["S", "M"]},
        variants=[
            Variant(
                id="v1",
                sku="TEE-S",
                options={"Size": "S"},
                price_amount=19.99,
                inventory_quantity=4,
                weight=220,
            ),
            Variant(
                id="v2",
                sku="TEE-M",
                options={"Size": "M"},
                price_amount=21.99,
                inventory_quantity=2,
                weight=230,
            ),
        ],
        category="Shirts",
        tags=["tee", "v-neck"],
        raw={},
    )

    csv_text, _ = product_to_squarespace_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SQUARESPACE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Product Type"] == "physical"
    assert frame.loc[0, "Title"] == "Classic Tee"
    assert frame.loc[0, "Description"] == "Soft cotton tee"
    assert frame.loc[0, "SKU"] == "TEE-S"
    assert frame.loc[0, "Option Name 1"] == "Size"
    assert frame.loc[0, "Option Value 1"] == "S"
    assert frame.loc[0, "Visible"] == "TRUE"
    assert frame.loc[0, "Hosted Image URLs"] == "https://cdn.example.com/tee.jpg"
    assert frame.loc[1, "Product Type"] == ""
    assert frame.loc[1, "Title"] == ""
    assert frame.loc[1, "Description"] == ""
    assert frame.loc[1, "SKU"] == "TEE-M"
    assert frame.loc[1, "Option Name 1"] == "Size"
    assert frame.loc[1, "Option Value 1"] == "M"
    assert frame.loc[1, "Visible"] == ""
    assert frame.loc[1, "Hosted Image URLs"] == ""


def test_multiple_variants_without_options_synthesizes_option_column() -> None:
    product = ProductResult(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="Soft cotton tee",
        price={"amount": 19.99, "currency": "USD"},
        images=[],
        variants=[
            Variant(id="v1", sku="TEE-BLK", title="Black", price_amount=19.99),
            Variant(id="v2", sku="TEE-WHT", title="White", price_amount=21.99),
        ],
        raw={},
    )

    csv_text, _ = product_to_squarespace_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == SQUARESPACE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Option Name 1"] == "Option"
    assert frame.loc[0, "Option Value 1"] == "Black"
    assert frame.loc[1, "Option Name 1"] == "Option"
    assert frame.loc[1, "Option Value 1"] == "White"
