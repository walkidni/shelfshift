from app.services.exporters import product_to_bigcommerce_csv
from app.services.exporters.bigcommerce_csv import BIGCOMMERCE_COLUMNS
from app.services.importer import ProductResult, Variant
from tests._csv_helpers import read_frame


def test_bigcommerce_export_maps_product_and_sku_rows() -> None:
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
            ),
        ],
        tags=["tee", "cotton"],
        slug="classic-tee",
        raw={},
    )

    csv_text, filename = product_to_bigcommerce_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert filename == "bigcommerce-20260208T000000Z.csv"
    assert list(frame.columns) == BIGCOMMERCE_COLUMNS
    assert len(frame) == 3

    assert frame.loc[0, "Item Type"] == "Product"
    assert frame.loc[0, "Product Name"] == "Classic Tee"
    assert frame.loc[0, "Product Code/SKU"] == "SH-101"
    assert frame.loc[0, "Option Set"] == "Color, Size"
    assert frame.loc[0, "Product Description"] == "<p>Soft cotton tee</p>"
    assert frame.loc[0, "Price"] == "19.99"
    assert frame.loc[0, "Allow Purchases?"] == "Y"
    assert frame.loc[0, "Product Visible?"] == "N"
    assert frame.loc[0, "Track Inventory"] == "N"
    assert frame.loc[0, "Search Keywords"] == "cotton,tee"
    assert frame.loc[0, "Product Image File - 1"] == "https://cdn.example.com/tee-1.jpg"
    assert frame.loc[0, "Product Image File - 2"] == "https://cdn.example.com/tee-2.jpg"
    assert frame.loc[0, "Product URL"] == "classic-tee"

    assert frame.loc[1, "Item Type"] == "SKU"
    assert frame.loc[1, "Product Code/SKU"] == "TEE-BLK-M"
    assert frame.loc[1, "Product Name"] == "Classic Tee [S]Color=Black[/S] [S]Size=M[/S]"
    assert frame.loc[1, "Track Inventory"] == "Y"
    assert frame.loc[1, "Current Stock Level"] == "4"

    assert frame.loc[2, "Item Type"] == "SKU"
    assert frame.loc[2, "Product Code/SKU"] == "TEE-WHT-L"
    assert frame.loc[2, "Product Name"] == "Classic Tee [S]Color=White[/S] [S]Size=L[/S]"
    assert frame.loc[2, "Track Inventory"] == "Y"
    assert frame.loc[2, "Current Stock Level"] == "2"


def test_bigcommerce_export_simple_product_uses_single_product_row() -> None:
    product = ProductResult(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=["https://cdn.example.com/mug.jpg"],
        raw={},
    )

    csv_text, _ = product_to_bigcommerce_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == BIGCOMMERCE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Item Type"] == "Product"
    assert frame.loc[0, "Product Code/SKU"] == "AMZ-B000111"
    assert frame.loc[0, "Price"] == "12"
    assert frame.loc[0, "Product Visible?"] == "Y"
    assert frame.loc[0, "Track Inventory"] == "N"
    assert frame.loc[0, "Current Stock Level"] == ""
