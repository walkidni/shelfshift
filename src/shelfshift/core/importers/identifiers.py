from collections.abc import Mapping
from typing import Any

from ..canonical import Identifiers

RESERVED_IDENTIFIER_KEYS = frozenset(
    {
        "source_product_id",
        "source_variant_id",
        "sku",
        "barcode",
    }
)


def clean_identifier_values(values: Mapping[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not values:
        return out
    for key, value in values.items():
        key_str = str(key or "").strip()
        value_str = str(value or "").strip()
        if not key_str or not value_str:
            continue
        out[key_str] = value_str
    return out


def make_identifiers(values: Mapping[str, Any] | None = None) -> Identifiers:
    return Identifiers(values=clean_identifier_values(values))


def source_identifier_namespace(source: str, platform: str) -> str:
    source_token = str(source or "").strip().lower()
    platform_token = str(platform or "").strip().lower()
    if not source_token:
        source_token = "source"
    if not platform_token:
        platform_token = "unknown"
    return f"{source_token}:{platform_token}"


def source_identifier_key(source: str, platform: str, key: str) -> str:
    key_token = str(key or "").strip()
    if not key_token:
        return ""
    namespace = source_identifier_namespace(source, platform)
    prefix = f"{namespace}:"
    if key_token.startswith(prefix):
        return key_token
    return f"{prefix}{key_token}"


def set_identifier(
    target: Identifiers,
    *,
    key: str,
    value: Any,
    overwrite: bool = False,
) -> None:
    key_str = str(key or "").strip()
    value_str = str(value or "").strip()
    if not key_str or not value_str:
        return
    if not overwrite and key_str in target.values:
        return
    target.values[key_str] = value_str


def merge_identifier_values(
    target: Identifiers,
    values: Mapping[str, Any] | None,
    *,
    namespace: str | None = None,
    overwrite: bool = False,
) -> None:
    cleaned = clean_identifier_values(values)
    if not cleaned:
        return
    prefix = ""
    namespace_value = str(namespace or "").strip().rstrip(":").lower()
    if namespace_value:
        prefix = f"{namespace_value}:"
    for key, value in cleaned.items():
        resolved_key = key if not prefix or key.startswith(prefix) else f"{prefix}{key}"
        set_identifier(target, key=resolved_key, value=value, overwrite=overwrite)


__all__ = [
    "RESERVED_IDENTIFIER_KEYS",
    "clean_identifier_values",
    "make_identifiers",
    "merge_identifier_values",
    "set_identifier",
    "source_identifier_key",
    "source_identifier_namespace",
]
