from shelfshift.core.importers.identifiers import (
    RESERVED_IDENTIFIER_KEYS,
    make_identifiers,
    merge_identifier_values,
    set_identifier,
    source_identifier_key,
    source_identifier_namespace,
)


def test_make_identifiers_cleans_empty_values() -> None:
    identifiers = make_identifiers(
        {
            " source_product_id ": " 123 ",
            "": "x",
            "sku": "",
            "barcode": "  9988  ",
        }
    )

    assert identifiers.values == {
        "source_product_id": "123",
        "barcode": "9988",
    }


def test_set_identifier_respects_overwrite_flag() -> None:
    identifiers = make_identifiers({"sku": "SKU-1"})
    set_identifier(identifiers, key="sku", value="SKU-2")
    assert identifiers.values["sku"] == "SKU-1"

    set_identifier(identifiers, key="sku", value="SKU-2", overwrite=True)
    assert identifiers.values["sku"] == "SKU-2"


def test_merge_identifier_values_applies_namespace_and_preserves_existing() -> None:
    identifiers = make_identifiers({"csv:title": "Old"})
    merge_identifier_values(
        identifiers,
        {
            "title": "New",
            "seo_description": "Desc",
            "": "ignored",
        },
        namespace="csv",
    )
    assert identifiers.values["csv:title"] == "Old"
    assert identifiers.values["csv:seo_description"] == "Desc"


def test_reserved_identifier_keys_contract() -> None:
    assert {
        "source_product_id",
        "source_variant_id",
        "sku",
        "barcode",
    } == RESERVED_IDENTIFIER_KEYS


def test_source_identifier_namespace_and_key() -> None:
    assert source_identifier_namespace("csv", "Shopify") == "csv:shopify"
    assert source_identifier_key("url", "squarespace", "mpn") == "url:squarespace:mpn"
