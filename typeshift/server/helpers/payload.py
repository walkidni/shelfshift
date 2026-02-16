"""Product payload encoding/decoding helpers for web routes."""

from __future__ import annotations

import base64
import json

from fastapi import HTTPException

from ...core.api import parse_product_payload
from ...core.canonical.entities import Product
from ...core.canonical.serialization import serialize_product_for_api


def decode_product_json_b64(encoded: str) -> dict | list[dict]:
    try:
        payload = base64.b64decode(str(encoded or "").encode("utf-8"), validate=True)
        data = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid product preview payload.") from exc
    if isinstance(data, list):
        if not all(isinstance(item, dict) for item in data):
            raise HTTPException(status_code=422, detail="Invalid product preview payload.")
        return data
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Invalid product preview payload.")
    return data


def product_to_json_b64(product: Product) -> str:
    payload = serialize_product_for_api(product, include_raw=False)
    return base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("utf-8")


def products_to_json_b64(products: list[Product]) -> str:
    payloads = [serialize_product_for_api(product, include_raw=False) for product in products]
    return base64.b64encode(json.dumps(payloads, ensure_ascii=False).encode("utf-8")).decode("utf-8")


def product_from_payload_dict(payload: dict) -> Product:
    try:
        parsed = parse_product_payload(payload)
        if isinstance(parsed, list):
            raise ValueError("Expected one product object.")
        return parsed
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid product payload: {exc}") from exc
