from app.services.csv_importers.batch import import_products_from_csv


def test_import_products_from_csv_shopify_parses_multiple_products() -> None:
    csv_text = "\n".join(
        [
            "Handle,Title,Body (HTML),Variant SKU,Variant Price",
            "alpha,Alpha Product,Alpha description,ALPHA-1,10.00",
            "beta,Beta Product,Beta description,BETA-1,12.00",
        ]
    )

    products = import_products_from_csv(
        source_platform="shopify",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="",
    )

    assert len(products) == 2
    assert products[0].source.platform == "shopify"
    assert products[0].source.slug == "alpha"
    assert products[0].title == "Alpha Product"
    assert products[1].source.slug == "beta"
    assert products[1].title == "Beta Product"

