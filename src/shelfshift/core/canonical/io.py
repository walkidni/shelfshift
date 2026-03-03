"""Canonical JSON payload hydration helpers."""

import json
from pathlib import Path
from typing import Any

from .entities import Product, Variant


def json_to_product(
    payload: dict[str, Any] | str | bytes | Path,
    *,
    from_file: bool = False,
) -> Product:
    loaded = _load_json_payload(payload, from_file=from_file)
    if not isinstance(loaded, dict):
        raise ValueError("json_to_product expects a JSON object payload.")
    return _payload_to_product(loaded)


def json_to_products(
    payload: list[dict[str, Any]] | str | bytes | Path,
    *,
    from_file: bool = False,
) -> list[Product]:
    loaded = _load_json_payload(payload, from_file=from_file)
    if not isinstance(loaded, list):
        raise ValueError("json_to_products expects a JSON array payload.")
    return [json_to_product(item) for item in loaded]


def _payload_to_product(payload: dict[str, Any]) -> Product:
    variants_payload = payload.get("variants")
    variants: list[Variant] = []
    if isinstance(variants_payload, list):
        for item in variants_payload:
            if isinstance(item, dict):
                variants.append(Variant(**item))

    product_payload = dict(payload)
    product_payload["variants"] = variants
    return Product(**product_payload)


def _load_json_payload(value: Any, *, from_file: bool) -> Any:
    if from_file:
        path = Path(value)
        return json.loads(path.read_text(encoding="utf-8"))

    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, bytes):
        try:
            return json.loads(value.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise ValueError("JSON bytes input must be UTF-8 encoded.") from exc

    if isinstance(value, str):
        return json.loads(value)

    if isinstance(value, Path):
        return json.loads(value.read_text(encoding="utf-8"))

    raise ValueError("JSON payload must be dict/list, JSON string/bytes, or a file path.")


__all__ = ["json_to_product", "json_to_products"]
