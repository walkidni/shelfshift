import io

import pandas as pd
import pytest

from shelfshift.core.exporters.shared.batch import products_to_shopify_csv
from shelfshift.core.exporters.shared.batch import (
    products_to_bigcommerce_csv,
    products_to_squarespace_csv,
    products_to_wix_csv,
    products_to_woocommerce_csv,
)
from shelfshift.core.exporters.platforms.bigcommerce import BIGCOMMERCE_COLUMNS
from shelfshift.core.exporters.platforms.shopify import SHOPIFY_COLUMNS
from shelfshift.core.exporters.platforms.squarespace import SQUARESPACE_COLUMNS
from shelfshift.core.exporters.platforms.wix import WIX_COLUMNS
from shelfshift.core.exporters.platforms.woocommerce import WOOCOMMERCE_COLUMNS
from tests.helpers._model_builders import Product, Variant


def test_products_to_shopify_csv_combines_multiple_products() -> None:
    alpha = Product(
        source={"platform": "shopify", "id": "1", "slug": "alpha"},
        title="Alpha Product",
        description="Alpha description",
        images=["https://cdn.example.com/alpha.jpg"],
        variants=[Variant(id="v1", sku="ALPHA-1", price_amount=10.0, inventory_quantity=3)],
        tags=["alpha"],
    )
    beta = Product(
        source={"platform": "shopify", "id": "2", "slug": "beta"},
        title="Beta Product",
        description="Beta description",
        images=["https://cdn.example.com/beta.jpg"],
        variants=[Variant(id="v1", sku="BETA-1", price_amount=12.0, inventory_quantity=5)],
        tags=["beta"],
    )

    csv_text, filename = products_to_shopify_csv([alpha, beta], publish=False, weight_unit="g")

    assert filename.endswith(".csv")
    frame = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == SHOPIFY_COLUMNS
    assert list(frame["Handle"])[:2] == ["alpha", "beta"]


def test_products_to_shopify_csv_rejects_duplicate_handles() -> None:
    alpha = Product(
        source={"platform": "shopify", "id": "1", "slug": "alpha"},
        title="Alpha Product",
        variants=[Variant(id="v1", sku="ALPHA-1", price_amount=10.0)],
    )
    duplicate = Product(
        source={"platform": "shopify", "id": "2", "slug": "alpha"},
        title="Duplicate Product",
        variants=[Variant(id="v1", sku="DUP-1", price_amount=10.0)],
    )

    with pytest.raises(ValueError, match="Duplicate Shopify Handle"):
        products_to_shopify_csv([alpha, duplicate], publish=False, weight_unit="g")


def test_products_to_bigcommerce_csv_combines_multiple_products_modern() -> None:
    alpha = Product(
        source={"platform": "shopify", "id": "123", "slug": "alpha"},
        title="Alpha Product",
        variants=[Variant(id="v1", sku="ALPHA-1", price_amount=10.0, inventory_quantity=3)],
        images=[],
    )
    beta = Product(
        source={"platform": "shopify", "id": "456", "slug": "beta"},
        title="Beta Product",
        variants=[Variant(id="v1", sku="BETA-1", price_amount=12.0, inventory_quantity=5)],
        images=[],
    )

    csv_text, _ = products_to_bigcommerce_csv(
        [alpha, beta],
        publish=False,
        csv_format="modern",
        weight_unit="kg",
    )

    frame = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == BIGCOMMERCE_COLUMNS
    product_rows = frame[frame["Item"] == "Product"]
    assert len(product_rows) == 2


def test_products_to_bigcommerce_csv_rejects_duplicate_skus_modern() -> None:
    alpha = Product(
        source={"platform": "shopify", "id": "123", "slug": "alpha"},
        title="Alpha Product",
        variants=[Variant(id="v1", sku="DUP-1", price_amount=10.0)],
    )
    duplicate = Product(
        source={"platform": "shopify", "id": "123", "slug": "alpha-dup"},
        title="Duplicate Product",
        variants=[Variant(id="v1", sku="DUP-1", price_amount=10.0)],
    )

    with pytest.raises(ValueError, match="Duplicate BigCommerce SKU"):
        products_to_bigcommerce_csv([alpha, duplicate], publish=False, csv_format="modern", weight_unit="kg")


def test_products_to_bigcommerce_csv_rejects_duplicate_codes_legacy() -> None:
    alpha = Product(
        source={"platform": "shopify", "id": "123", "slug": "alpha"},
        title="Alpha Product",
        variants=[Variant(id="v1", sku="CODE-1", price_amount=10.0)],
    )
    duplicate = Product(
        source={"platform": "shopify", "id": "456", "slug": "beta"},
        title="Duplicate Product",
        variants=[Variant(id="v1", sku="CODE-1", price_amount=10.0)],
    )

    with pytest.raises(ValueError, match="Duplicate BigCommerce Code"):
        products_to_bigcommerce_csv([alpha, duplicate], publish=False, csv_format="legacy", weight_unit="kg")


def test_products_to_wix_csv_combines_multiple_products() -> None:
    alpha = Product(
        source={"platform": "shopify", "id": "1", "slug": "alpha"},
        title="Alpha Product",
        variants=[Variant(id="v1", sku="ALPHA-1", price_amount=10.0, inventory_quantity=3)],
        images=["https://cdn.example.com/alpha.jpg"],
    )
    beta = Product(
        source={"platform": "shopify", "id": "2", "slug": "beta"},
        title="Beta Product",
        variants=[Variant(id="v1", sku="BETA-1", price_amount=12.0, inventory_quantity=5)],
        images=["https://cdn.example.com/beta.jpg"],
    )

    csv_text, _ = products_to_wix_csv([alpha, beta], publish=False, weight_unit="kg")

    frame = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == WIX_COLUMNS
    product_rows = frame[frame["fieldType"] == "PRODUCT"]
    assert list(product_rows["handle"]) == ["alpha", "beta"]


def test_products_to_wix_csv_rejects_duplicate_handles() -> None:
    alpha = Product(
        source={"platform": "shopify", "id": "1", "slug": "alpha"},
        title="Alpha Product",
        variants=[Variant(id="v1", sku="ALPHA-1", price_amount=10.0)],
    )
    duplicate = Product(
        source={"platform": "shopify", "id": "2", "slug": "alpha"},
        title="Duplicate Product",
        variants=[Variant(id="v1", sku="DUP-1", price_amount=10.0)],
    )

    with pytest.raises(ValueError, match="Duplicate Wix handle"):
        products_to_wix_csv([alpha, duplicate], publish=False, weight_unit="kg")


def test_products_to_woocommerce_csv_combines_multiple_products() -> None:
    alpha = Product(
        source={"platform": "shopify", "id": "123", "slug": "alpha"},
        title="Alpha Product",
        variants=[Variant(id="v1", sku="ALPHA-1", price_amount=10.0, inventory_quantity=3)],
        images=[],
    )
    beta = Product(
        source={"platform": "shopify", "id": "456", "slug": "beta"},
        title="Beta Product",
        variants=[Variant(id="v1", sku="BETA-1", price_amount=12.0, inventory_quantity=5)],
        images=[],
    )

    csv_text, _ = products_to_woocommerce_csv([alpha, beta], publish=False, weight_unit="kg")

    frame = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == WOOCOMMERCE_COLUMNS
    assert len(frame) == 2


def test_products_to_woocommerce_csv_rejects_duplicate_parent_skus() -> None:
    alpha = Product(
        source={"platform": "shopify", "id": "123", "slug": "alpha"},
        title="Alpha Product",
        variants=[Variant(id="v1", sku="ALPHA-1", price_amount=10.0)],
    )
    duplicate = Product(
        source={"platform": "shopify", "id": "123", "slug": "alpha-dup"},
        title="Duplicate Product",
        variants=[Variant(id="v1", sku="DUP-1", price_amount=10.0)],
    )

    with pytest.raises(ValueError, match="Duplicate WooCommerce parent SKU"):
        products_to_woocommerce_csv([alpha, duplicate], publish=False, weight_unit="kg")


def test_products_to_squarespace_csv_leaves_product_page_and_url_blank() -> None:
    alpha = Product(
        source={"platform": "shopify", "id": "1", "slug": "alpha"},
        title="Alpha Product",
        variants=[Variant(id="v1", sku="ALPHA-1", price_amount=10.0, inventory_quantity=3)],
        images=[],
    )
    beta = Product(
        source={"platform": "shopify", "id": "2", "slug": "beta"},
        title="Beta Product",
        variants=[Variant(id="v1", sku="BETA-1", price_amount=12.0, inventory_quantity=5)],
        images=[],
    )

    csv_text, _ = products_to_squarespace_csv([alpha, beta], publish=False, product_page="", product_url="", weight_unit="kg")

    frame = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == SQUARESPACE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Product Page"] == ""
    assert frame.loc[0, "Product URL"] == ""
