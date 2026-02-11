from app.services.exporters import product_to_bigcommerce_csv
from app.services.exporters.bigcommerce_csv import BIGCOMMERCE_COLUMNS
from app.services.importer import ProductResult, Variant
from tests._csv_helpers import read_frame


def test_bigcommerce_export_emits_modern_v3_product_variant_image_rows() -> None:
    product = ProductResult(
        platform="shopify",
        id="101",
        title="Classic Tee",
        description="<p>Soft cotton tee</p>",
        price={"amount": 19.99, "currency": "USD"},
        images=[
            "https://cdn.example.com/tee-1.jpg",
            "https://cdn.example.com/tee-2.jpg",
        ],
        options={"Color": ["Black", "White"], "Size": ["M", "L"]},
        variants=[
            Variant(
                id="v1",
                sku="TEE-BLK-M",
                options={"Color": "Black", "Size": "M"},
                price_amount=19.99,
                inventory_quantity=4,
                weight=220,
                image="https://cdn.example.com/tee-black-m.jpg",
            ),
            Variant(
                id="v2",
                sku="TEE-WHT-L",
                options={"Color": "White", "Size": "L"},
                price_amount=21.99,
                inventory_quantity=2,
                weight=230,
                image="//cdn.example.com/tee-white-l.jpg",
            ),
        ],
        slug="classic-tee",
        raw={},
    )

    csv_text, filename = product_to_bigcommerce_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert filename == "bigcommerce-20260208T000000Z.csv"
    assert list(frame.columns) == BIGCOMMERCE_COLUMNS
    assert len(frame) == 5

    assert frame.loc[0, "Item Type"] == "Product"
    assert frame.loc[0, "Type"] == "physical"
    assert frame.loc[0, "Name"] == "Classic Tee"
    assert frame.loc[0, "Description"] == "<p>Soft cotton tee</p>"
    assert frame.loc[0, "SKU"] == "SH-101"
    assert frame.loc[0, "Price"] == "19.99"
    assert frame.loc[0, "Weight"] == "0.22"
    assert frame.loc[0, "Inventory"] == "variant"

    assert frame.loc[1, "Item Type"] == "Variant"
    assert frame.loc[1, "SKU"] == "TEE-BLK-M"
    assert frame.loc[1, "Options"] == "Color=Black,Size=M"
    assert frame.loc[1, "Variant Image URL"] == "https://cdn.example.com/tee-black-m.jpg"

    assert frame.loc[2, "Item Type"] == "Variant"
    assert frame.loc[2, "SKU"] == "TEE-WHT-L"
    assert frame.loc[2, "Options"] == "Color=White,Size=L"
    assert frame.loc[2, "Variant Image URL"] == "https://cdn.example.com/tee-white-l.jpg"

    assert frame.loc[3, "Item Type"] == "Image"
    assert frame.loc[3, "Image URL (Import)"] == "https://cdn.example.com/tee-1.jpg"
    assert frame.loc[3, "Image Is Thumbnail?"] == "TRUE"

    assert frame.loc[4, "Item Type"] == "Image"
    assert frame.loc[4, "Image URL (Import)"] == "https://cdn.example.com/tee-2.jpg"
    assert frame.loc[4, "Image Is Thumbnail?"] == "FALSE"


def test_bigcommerce_export_simple_product_uses_product_and_image_rows() -> None:
    product = ProductResult(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=["https://cdn.example.com/mug.jpg"],
        variants=[Variant(id="v1", sku="MUG-001", price_amount=12.0, image="//cdn.example.com/mug-variant.jpg")],
        raw={},
    )

    csv_text, _ = product_to_bigcommerce_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == BIGCOMMERCE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Item Type"] == "Product"
    assert frame.loc[0, "Type"] == "physical"
    assert frame.loc[0, "SKU"] == "MUG-001"
    assert frame.loc[0, "Price"] == "12"
    assert frame.loc[0, "Inventory"] == "none"
    assert frame.loc[0, "Variant Image URL"] == "https://cdn.example.com/mug-variant.jpg"
    assert frame.loc[1, "Item Type"] == "Image"
    assert frame.loc[1, "Image URL (Import)"] == "https://cdn.example.com/mug.jpg"
