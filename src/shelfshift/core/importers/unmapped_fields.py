from collections.abc import Mapping
from typing import Any


def clean_unmapped_fields(values: Mapping[str, Any] | None) -> dict[str, str]:
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


def platform_unmapped_key(platform: str, key: str) -> str:
    key_token = str(key or "").strip()
    if not key_token:
        return ""
    platform_token = str(platform or "").strip().lower() or "unknown"
    prefix = f"{platform_token}:"
    if key_token.startswith(prefix):
        return key_token
    return f"{prefix}{key_token}"


def set_unmapped_field(
    target: dict[str, str],
    *,
    key: str,
    value: Any,
    overwrite: bool = False,
) -> None:
    key_str = str(key or "").strip()
    value_str = str(value or "").strip()
    if not key_str or not value_str:
        return
    if not overwrite and key_str in target:
        return
    target[key_str] = value_str


def merge_unmapped_fields(
    target: dict[str, str],
    values: Mapping[str, Any] | None,
    *,
    platform: str,
    overwrite: bool = False,
) -> None:
    cleaned = clean_unmapped_fields(values)
    if not cleaned:
        return
    for key, value in cleaned.items():
        set_unmapped_field(
            target,
            key=platform_unmapped_key(platform, key),
            value=value,
            overwrite=overwrite,
        )


__all__ = [
    "clean_unmapped_fields",
    "merge_unmapped_fields",
    "platform_unmapped_key",
    "set_unmapped_field",
]
