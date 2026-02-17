"""Stable public API facade for the Typeshift core engine."""


from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.services.csv_importers import parse_canonical_product_payload

from .canonical.entities import Product
from .config import CoreConfig, config_from_env
from .detect import detect_csv_platform as _detect_csv_platform
from .detect import detect_product_url as _detect_product_url
from .importers.csv import import_product_from_csv, import_products_from_csv
from .importers.url import import_product_from_url, import_products_from_urls
from .registry import get_exporter
from .validate import ValidationReport, validate_product


@dataclass(frozen=True)
class DetectResult:
    kind: str
    platform: str | None
    is_product: bool
    product_id: str | None = None
    slug: str | None = None


@dataclass
class ImportResult:
    products: list[Product] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ExportResult:
    csv_bytes: bytes
    filename: str


def detect_url(url: str) -> DetectResult:
    payload = _detect_product_url(url)
    return DetectResult(
        kind="url",
        platform=payload.get("platform"),
        is_product=bool(payload.get("is_product", False)),
        product_id=payload.get("product_id"),
        slug=payload.get("slug"),
    )


def detect_csv(csv_input: bytes | str | Path) -> DetectResult:
    csv_bytes = _coerce_bytes(csv_input)
    platform = _detect_csv_platform(csv_bytes)
    return DetectResult(kind="csv", platform=platform, is_product=False)


def import_url(
    urls: str | list[str],
    *,
    strict: bool = False,
    debug: bool = False,
    rapidapi_key: str | None = None,
) -> ImportResult:
    config = config_from_env(strict=strict, debug=debug)
    resolved_rapidapi_key = rapidapi_key if rapidapi_key is not None else config.rapidapi_key

    try:
        from app.helpers import importing as _legacy_importing
    except Exception:
        _legacy_importing = None

    if isinstance(urls, str):
        if _legacy_importing is not None:
            try:
                product = _legacy_importing.run_import_product(urls)
            except HTTPException as exc:
                raise ValueError(str(exc.detail)) from exc
        else:
            product = import_product_from_url(urls, rapidapi_key=resolved_rapidapi_key)
        return ImportResult(products=[product], errors=[])

    if _legacy_importing is not None:
        products, errors = _legacy_importing.run_import_products(list(urls))
        if strict and errors:
            raise ValueError(f"Strict mode failed with {len(errors)} URL import error(s).")
        return ImportResult(products=products, errors=errors)

    products, errors = import_products_from_urls(
        list(urls),
        rapidapi_key=resolved_rapidapi_key,
    )
    if strict and errors:
        raise ValueError(f"Strict mode failed with {len(errors)} URL import error(s).")
    return ImportResult(products=products, errors=errors)


def import_csv(
    csv_input: bytes | str | Path,
    *,
    platform: str | None = None,
    strict: bool = False,
    source_weight_unit: str | None = None,
) -> ImportResult:
    csv_bytes = _coerce_bytes(csv_input)
    source_platform = (platform or _detect_csv_platform(csv_bytes)).strip().lower()
    try:
        from app.helpers import importing as _legacy_importing
    except Exception:
        _legacy_importing = None

    if _legacy_importing is not None:
        products = _legacy_importing.run_import_csv_products(
            source_platform=source_platform,
            csv_bytes=csv_bytes,
            source_weight_unit=source_weight_unit,
        )
    else:
        products = import_products_from_csv(
            source_platform=source_platform,
            csv_bytes=csv_bytes,
            source_weight_unit=source_weight_unit,
        )
    if strict and not products:
        raise ValueError("Strict mode failed: no products imported from CSV.")
    return ImportResult(products=products, errors=[])


def export_csv(
    products: Product | list[Product],
    *,
    target: str,
    options: dict[str, Any] | None = None,
) -> ExportResult:
    normalized_target = str(target).strip().lower()
    opts = dict(options or {})

    publish = bool(opts.get("publish", False))
    weight_unit = str(opts.get("weight_unit", ""))
    bigcommerce_csv_format = str(opts.get("bigcommerce_csv_format", "modern"))
    squarespace_product_page = str(opts.get("squarespace_product_page", ""))
    squarespace_product_url = str(opts.get("squarespace_product_url", ""))

    try:
        exporter = get_exporter(normalized_target)
    except KeyError as exc:
        raise ValueError(
            "target_platform must be one of: shopify, bigcommerce, wix, squarespace, woocommerce"
        ) from exc

    if isinstance(products, list):
        from app.services.exporters.batch import (
            products_to_bigcommerce_csv,
            products_to_shopify_csv,
            products_to_squarespace_csv,
            products_to_wix_csv,
            products_to_woocommerce_csv,
        )

        if normalized_target == "shopify":
            csv_text, filename = products_to_shopify_csv(products, publish=publish, weight_unit=weight_unit)
        elif normalized_target == "bigcommerce":
            csv_text, filename = products_to_bigcommerce_csv(
                products,
                publish=publish,
                csv_format=bigcommerce_csv_format,
                weight_unit=weight_unit,
            )
        elif normalized_target == "wix":
            csv_text, filename = products_to_wix_csv(products, publish=publish, weight_unit=weight_unit)
        elif normalized_target == "squarespace":
            csv_text, filename = products_to_squarespace_csv(
                products,
                publish=publish,
                product_page=squarespace_product_page,
                product_url=squarespace_product_url,
                weight_unit=weight_unit,
            )
        elif normalized_target == "woocommerce":
            csv_text, filename = products_to_woocommerce_csv(products, publish=publish, weight_unit=weight_unit)
        else:
            raise ValueError(f"Unsupported target platform: {normalized_target}")
        return ExportResult(csv_bytes=csv_text.encode("utf-8"), filename=filename)

    csv_text, filename = exporter(
        products,
        target_platform=normalized_target,
        publish=publish,
        weight_unit=weight_unit,
        bigcommerce_csv_format=bigcommerce_csv_format,
        squarespace_product_page=squarespace_product_page,
        squarespace_product_url=squarespace_product_url,
    )
    return ExportResult(csv_bytes=csv_text.encode("utf-8"), filename=filename)


def convert_csv(
    csv_input: bytes | str | Path,
    *,
    target: str,
    source: str | None = None,
    strict: bool = False,
    source_weight_unit: str | None = None,
    export_options: dict[str, Any] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    imported = import_csv(
        csv_input,
        platform=source,
        strict=strict,
        source_weight_unit=source_weight_unit,
    )
    exported = export_csv(imported.products, target=target, options=export_options)

    report = {
        "source_platform": source or _detect_csv_platform(_coerce_bytes(csv_input)),
        "target_platform": str(target).strip().lower(),
        "product_count": len(imported.products),
        "errors": imported.errors,
        "filename": exported.filename,
    }
    return exported.csv_bytes, report


def validate(products: Product | list[Product]) -> list[ValidationReport]:
    if isinstance(products, list):
        return [validate_product(product) for product in products]
    return [validate_product(products)]


def parse_product_payload(payload: dict[str, Any] | list[dict[str, Any]]) -> Product | list[Product]:
    if isinstance(payload, list):
        return [parse_canonical_product_payload(item) for item in payload]
    return parse_canonical_product_payload(payload)


def _coerce_bytes(value: bytes | str | Path) -> bytes:
    if isinstance(value, bytes):
        return value
    path = Path(value)
    return path.read_bytes()


__all__ = [
    "CoreConfig",
    "DetectResult",
    "ExportResult",
    "ImportResult",
    "config_from_env",
    "convert_csv",
    "detect_csv",
    "detect_url",
    "export_csv",
    "import_csv",
    "import_url",
    "parse_product_payload",
    "validate",
]
