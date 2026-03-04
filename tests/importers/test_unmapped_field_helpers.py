from shelfshift.core.importers.unmapped_fields import (
    clean_unmapped_fields,
    merge_unmapped_fields,
    platform_unmapped_key,
    set_unmapped_field,
)


def test_clean_unmapped_fields_drops_empty_entries() -> None:
    cleaned = clean_unmapped_fields({" a ": " 1 ", "": "x", "b": ""})
    assert cleaned == {"a": "1"}


def test_platform_unmapped_key_prefixes_platform() -> None:
    assert platform_unmapped_key("Shopify", "type") == "shopify:type"
    assert platform_unmapped_key("shopify", "shopify:type") == "shopify:type"


def test_set_unmapped_field_respects_overwrite() -> None:
    target = {"shopify:type": "Graphic shirt"}
    set_unmapped_field(target, key="shopify:type", value="Apparel")
    assert target["shopify:type"] == "Graphic shirt"

    set_unmapped_field(target, key="shopify:type", value="Apparel", overwrite=True)
    assert target["shopify:type"] == "Apparel"


def test_merge_unmapped_fields_namespaces_by_platform() -> None:
    target = {"shopify:type": "Graphic shirt"}
    merge_unmapped_fields(
        target,
        {
            "type": "Ignore",
            "custom": "Value",
        },
        platform="shopify",
    )
    assert target["shopify:type"] == "Graphic shirt"
    assert target["shopify:custom"] == "Value"
