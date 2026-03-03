from __future__ import annotations

import shelfshift.core.canonical as canonical

_EXPECTED_CANONICAL_FACADE_EXPORTS = {
    "Currency",
    "CategorySet",
    "Identifiers",
    "Inventory",
    "Media",
    "MediaType",
    "Money",
    "OptionDef",
    "OptionValue",
    "Price",
    "Product",
    "Seo",
    "SourceRef",
    "Variant",
    "Weight",
    "WeightUnit",
    "json_to_product",
    "json_to_products",
}

_REMOVED_CANONICAL_FACADE_EXPORTS = {
    "format_decimal",
    "normalize_currency",
    "parse_decimal_money",
    "resolve_all_image_urls",
    "resolve_current_money",
    "resolve_option_defs",
    "resolve_primary_image_url",
    "resolve_taxonomy_paths",
    "resolve_variant_option_values",
    "serialize_product_for_api",
    "serialize_variant_for_api",
    "parse_product_payload",
}


def test_canonical_facade_exports_curated_surface() -> None:
    assert set(canonical.__all__) == _EXPECTED_CANONICAL_FACADE_EXPORTS


def test_canonical_facade_does_not_export_helpers_or_serializers() -> None:
    for name in _REMOVED_CANONICAL_FACADE_EXPORTS:
        assert name not in canonical.__all__
        assert not hasattr(canonical, name)
