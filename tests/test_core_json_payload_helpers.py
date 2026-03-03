from __future__ import annotations

import json
from pathlib import Path

from shelfshift.core import api as core_api
from shelfshift.core.canonical import io as canonical_io
from shelfshift.core.canonical.entities import Product


def test_core_api_json_helpers_alias_canonical_io() -> None:
    assert core_api.json_to_product is canonical_io.json_to_product
    assert core_api.json_to_products is canonical_io.json_to_products


def test_parse_product_payload_not_exposed_anywhere() -> None:
    assert not hasattr(canonical_io, "parse_product_payload")
    assert not hasattr(core_api, "parse_product_payload")


def test_json_to_product_parses_dict_payload() -> None:
    result = canonical_io.json_to_product({"source": {"platform": "shopify"}, "title": "Demo"})
    assert isinstance(result, Product)
    assert result.source.platform == "shopify"
    assert result.title == "Demo"


def test_json_to_product_and_json_to_products_cover_single_and_list_payloads() -> None:
    single = canonical_io.json_to_product({"source": {"platform": "shopify"}, "title": "One"})
    many = canonical_io.json_to_products(
        '[{"source":{"platform":"shopify"},"title":"One"},{"source":{"platform":"shopify"},"title":"Two"}]'
    )
    assert isinstance(single, Product)
    assert isinstance(many, list)
    assert len(many) == 2
    assert all(isinstance(item, Product) for item in many)


def test_json_to_product_parses_json_string() -> None:
    result = canonical_io.json_to_product('{"source":{"platform":"shopify"},"title":"Demo"}')
    assert isinstance(result, Product)
    assert result.source.platform == "shopify"
    assert result.title == "Demo"


def test_json_to_product_from_file_reads_path(tmp_path: Path) -> None:
    payload_path = tmp_path / "product.json"
    payload_path.write_text(
        json.dumps({"source": {"platform": "shopify"}, "title": "From file"}),
        encoding="utf-8",
    )

    result = canonical_io.json_to_product(payload_path, from_file=True)
    assert isinstance(result, Product)
    assert result.title == "From file"


def test_json_to_products_uses_json_to_product_for_each_payload(monkeypatch) -> None:
    calls: list[tuple[object, bool]] = []

    def fake_json_to_product(payload, *, from_file=False):
        calls.append((payload, from_file))
        return {"parsed": payload}

    monkeypatch.setattr(canonical_io, "json_to_product", fake_json_to_product)

    result = canonical_io.json_to_products(
        [
            {"source": {"platform": "shopify"}, "title": "One"},
            {"source": {"platform": "shopify"}, "title": "Two"},
        ]
    )

    assert result == [
        {"parsed": {"source": {"platform": "shopify"}, "title": "One"}},
        {"parsed": {"source": {"platform": "shopify"}, "title": "Two"}},
    ]
    assert calls == [
        ({"source": {"platform": "shopify"}, "title": "One"}, False),
        ({"source": {"platform": "shopify"}, "title": "Two"}, False),
    ]


def test_json_to_products_parses_json_array_string(monkeypatch) -> None:
    calls: list[tuple[object, bool]] = []

    def fake_json_to_product(payload, *, from_file=False):
        calls.append((payload, from_file))
        return {"parsed": payload}

    monkeypatch.setattr(canonical_io, "json_to_product", fake_json_to_product)

    result = canonical_io.json_to_products(
        '[{"source":{"platform":"shopify"},"title":"One"},{"source":{"platform":"shopify"},"title":"Two"}]'
    )

    assert result == [
        {"parsed": {"source": {"platform": "shopify"}, "title": "One"}},
        {"parsed": {"source": {"platform": "shopify"}, "title": "Two"}},
    ]
    assert calls == [
        ({"source": {"platform": "shopify"}, "title": "One"}, False),
        ({"source": {"platform": "shopify"}, "title": "Two"}, False),
    ]


def test_import_json_uses_json_to_product_for_single_payload(monkeypatch) -> None:
    calls: list[tuple[object, bool]] = []
    sentinel = object()

    def fake_json_to_product(payload, *, from_file=False):
        calls.append((payload, from_file))
        return sentinel

    monkeypatch.setattr(core_api, "json_to_product", fake_json_to_product)

    result = core_api.import_json({"source": {"platform": "shopify"}, "title": "One"})

    assert result.products == [sentinel]
    assert result.errors == []
    assert calls == [({"source": {"platform": "shopify"}, "title": "One"}, False)]


def test_import_json_uses_json_to_products_for_list_payload(monkeypatch) -> None:
    calls: list[tuple[object, bool]] = []
    sentinels = [object(), object()]

    def fake_json_to_products(payload, *, from_file=False):
        calls.append((payload, from_file))
        return sentinels

    monkeypatch.setattr(core_api, "json_to_products", fake_json_to_products)

    payload = [
        {"source": {"platform": "shopify"}, "title": "One"},
        {"source": {"platform": "shopify"}, "title": "Two"},
    ]
    result = core_api.import_json(payload)

    assert result.products == sentinels
    assert result.errors == []
    assert calls == [(payload, False)]
