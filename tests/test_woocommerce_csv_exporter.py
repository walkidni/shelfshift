from app.services.exporters import product_to_woocommerce_csv
from app.services.exporters.woocommerce_csv import WOOCOMMERCE_COLUMNS
from app.models import ProductResult, Variant
from tests._csv_helpers import read_frame


def test_simple_product_maps_qty_stock() -> None:
    product = ProductResult(
        platform="amazon",
        id="B000111",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=["https://cdn.example.com/mug.jpg"],
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

    csv_text, filename = product_to_woocommerce_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert filename == "woocommerce-20260208T000000Z.csv"
    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Type"] == "simple"
    assert frame.loc[0, "SKU"] == "AMZ:b000111"
    assert frame.loc[0, "Parent"] == ""
    assert frame.loc[0, "Published"] == "0"
    assert frame.loc[0, "Short description"] == "Demo description"
    assert frame.loc[0, "Description"] == "Demo description"
    assert frame.loc[0, "Regular price"] == "12"
    assert frame.loc[0, "Weight (kg)"] == "0.25"
    assert frame.loc[0, "Stock"] == "0"
    assert frame.loc[0, "In stock?"] == "0"


def test_variable_product_uses_namespaced_parent_and_variation_skus() -> None:
    product = ProductResult(
        platform="aliexpress",
        id="1005008518647948",
        title="Therapy Mask",
        description="Mask description",
        price={"amount": 50.4, "currency": "USD"},
        images=["https://cdn.example.com/mask-main.jpg"],
        options={"Color": ["Only Face mask", "Only Neck White"]},
        variants=[
            Variant(
                id="12000055918704602",
                sku="AE:1005008518647948:12000055918704602",
                options={"Color": "Only Face mask"},
                price_amount=50.4,
                inventory_quantity=10,
                image="https://cdn.example.com/mask-face.jpg",
            ),
            Variant(
                id="12000055918704603",
                sku="AE:1005008518647948:12000055918704603",
                options={"Color": "Only Neck White"},
                price_amount=50.4,
                inventory_quantity=0,
                image="https://cdn.example.com/mask-neck.jpg",
            ),
        ],
        raw={},
    )

    csv_text, _ = product_to_woocommerce_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "Type"] == "variable"
    assert frame.loc[0, "SKU"] == "AE:1005008518647948"
    assert frame.loc[0, "Short description"] == "Mask description"
    assert frame.loc[0, "Description"] == "Mask description"
    assert frame.loc[1, "Type"] == "variation"
    assert frame.loc[1, "SKU"] == "AE:1005008518647948:12000055918704602"
    assert frame.loc[1, "Short description"] == ""
    assert frame.loc[1, "Description"] == ""
    assert frame.loc[1, "Parent"] == "AE:1005008518647948"
    assert frame.loc[2, "SKU"] == "AE:1005008518647948:12000055918704603"
    assert frame.loc[2, "Short description"] == ""
    assert frame.loc[2, "Description"] == ""
    assert frame.loc[2, "Parent"] == "AE:1005008518647948"
    assert frame.loc[0, "Attribute 1 name"] == "Color"
    assert frame.loc[0, "Attribute 1 value(s)"] == "Only Face mask,Only Neck White"
    assert frame.loc[1, "Attribute 1 name"] == "Color"
    assert frame.loc[1, "Attribute 1 value(s)"] == "Only Face mask"
    assert frame.loc[2, "Attribute 1 value(s)"] == "Only Neck White"
    assert frame.loc[1, "Stock"] == "10"
    assert frame.loc[1, "In stock?"] == "1"
    assert frame.loc[2, "Stock"] == "0"
    assert frame.loc[2, "In stock?"] == "0"


def test_available_without_qty_does_not_emit_stock() -> None:
    product = ProductResult(
        platform="amazon",
        id="123456789",
        title="Digital Template",
        description="PDF template",
        price={"amount": 6.5, "currency": "USD"},
        images=[],
        variants=[Variant(id="v1", price_amount=6.5, available=False, inventory_quantity=None)],
        is_digital=True,
        raw={},
    )

    csv_text, _ = product_to_woocommerce_csv(product, publish=True)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 1
    assert frame.loc[0, "Type"] == "simple"
    assert frame.loc[0, "Tax status"] == "none"
    assert frame.loc[0, "In stock?"] == "0"
    assert frame.loc[0, "Stock"] == ""


def test_multiple_variants_without_options_synthesizes_option_attribute() -> None:
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

    csv_text, _ = product_to_woocommerce_csv(product, publish=False)
    frame = read_frame(csv_text)

    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 3
    assert frame.loc[0, "Attribute 1 name"] == "Option"
    assert frame.loc[0, "Attribute 1 value(s)"] == "Black,White"
    assert frame.loc[1, "Attribute 1 name"] == "Option"
    assert frame.loc[1, "Attribute 1 value(s)"] == "Black"
    assert frame.loc[2, "Attribute 1 value(s)"] == "White"
