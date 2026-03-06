import io

import pandas as pd
import pytest
from tests.helpers._model_builders import Product, Variant

from shelfshift.core.exporters.platforms.bigcommerce import BIGCOMMERCE_COLUMNS
from shelfshift.core.exporters.platforms.shopify import SHOPIFY_COLUMNS
from shelfshift.core.exporters.platforms.squarespace import SQUARESPACE_COLUMNS
from shelfshift.core.exporters.platforms.wix import WIX_COLUMNS
from shelfshift.core.exporters.platforms.woocommerce import woocommerce_columns_for_weight_unit
from shelfshift.core.exporters.shared.batch import (
    products_to_bigcommerce_csv,
    products_to_shopify_csv,
    products_to_squarespace_csv,
    products_to_wix_csv,
    products_to_woocommerce_csv,
)


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
    assert list(frame["URL handle"])[:2] == ["alpha", "beta"]


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
        products_to_bigcommerce_csv(
            [alpha, duplicate], publish=False, csv_format="modern", weight_unit="kg"
        )


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
        products_to_bigcommerce_csv(
            [alpha, duplicate], publish=False, csv_format="legacy", weight_unit="kg"
        )


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
    assert list(frame.columns) == woocommerce_columns_for_weight_unit("kg")
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

    csv_text, _ = products_to_squarespace_csv(
        [alpha, beta], publish=False, product_page="", product_url="", weight_unit="kg"
    )

    frame = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)
    assert list(frame.columns) == SQUARESPACE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "Product Page"] == ""
    assert frame.loc[0, "Product URL"] == ""


def test_batch_exporters_prefer_explicit_publish_over_product_visibility() -> None:
    product = Product(
        source={"platform": "shopify", "id": "1", "slug": "alpha"},
        title="Alpha Product",
        is_published=True,
        variants=[Variant(id="v1", sku="ALPHA-1", price_amount=10.0, inventory_quantity=3)],
        images=["https://cdn.example.com/alpha.jpg"],
    )

    shopify_csv, _ = products_to_shopify_csv([product], publish=False, weight_unit="g")
    shopify_frame = pd.read_csv(io.StringIO(shopify_csv), dtype=str, keep_default_na=False)
    assert shopify_frame.loc[0, "Published on online store"] == "FALSE"
    assert shopify_frame.loc[0, "Status"] == "Draft"

    bigcommerce_modern_csv, _ = products_to_bigcommerce_csv(
        [product],
        publish=False,
        csv_format="modern",
        weight_unit="kg",
    )
    bigcommerce_modern_frame = pd.read_csv(
        io.StringIO(bigcommerce_modern_csv),
        dtype=str,
        keep_default_na=False,
    )
    assert bigcommerce_modern_frame.loc[0, "Is Visible"] == "FALSE"

    bigcommerce_legacy_csv, _ = products_to_bigcommerce_csv(
        [product],
        publish=False,
        csv_format="legacy",
        weight_unit="kg",
    )
    bigcommerce_legacy_frame = pd.read_csv(
        io.StringIO(bigcommerce_legacy_csv),
        dtype=str,
        keep_default_na=False,
    )
    assert bigcommerce_legacy_frame.loc[0, "Product Visible?"] == "N"

    wix_csv, _ = products_to_wix_csv([product], publish=False, weight_unit="kg")
    wix_frame = pd.read_csv(io.StringIO(wix_csv), dtype=str, keep_default_na=False)
    assert set(wix_frame["visible"]) == {"FALSE"}

    squarespace_csv, _ = products_to_squarespace_csv(
        [product], publish=False, product_page="", product_url="", weight_unit="kg"
    )
    squarespace_frame = pd.read_csv(
        io.StringIO(squarespace_csv),
        dtype=str,
        keep_default_na=False,
    )
    assert squarespace_frame.loc[0, "Visible"] == "No"

    woocommerce_csv, _ = products_to_woocommerce_csv([product], publish=False, weight_unit="kg")
    woocommerce_frame = pd.read_csv(io.StringIO(woocommerce_csv), dtype=str, keep_default_na=False)
    assert woocommerce_frame.loc[0, "Published"] == "0"
    assert woocommerce_frame.loc[0, "Visibility in catalog"] == "hidden"


def test_batch_exporters_use_product_visibility_when_publish_is_none() -> None:
    product = Product(
        source={"platform": "shopify", "id": "1", "slug": "alpha"},
        title="Alpha Product",
        is_published=True,
        variants=[Variant(id="v1", sku="ALPHA-1", price_amount=10.0, inventory_quantity=3)],
        images=["https://cdn.example.com/alpha.jpg"],
    )

    shopify_csv, _ = products_to_shopify_csv([product], weight_unit="g")
    shopify_frame = pd.read_csv(io.StringIO(shopify_csv), dtype=str, keep_default_na=False)
    assert shopify_frame.loc[0, "Published on online store"] == "TRUE"
    assert shopify_frame.loc[0, "Status"] == "Active"
