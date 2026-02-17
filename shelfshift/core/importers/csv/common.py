import csv
import io
import re
from decimal import Decimal
from typing import Any, Iterable

from ...canonical import (
    CategorySet,
    Identifiers,
    Media,
    Money,
    OptionDef,
    Price,
    Product,
    Seo,
    SourceRef,
    Variant,
    Weight,
    parse_decimal_money,
)


MAX_CSV_UPLOAD_BYTES = 5 * 1024 * 1024
_HEADER_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def decode_csv_bytes(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV must be UTF-8 encoded.")


def csv_rows(csv_text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    headers = list(reader.fieldnames or [])
    if not headers:
        raise ValueError("CSV header row is required.")
    rows: list[dict[str, str]] = []
    for row in reader:
        rows.append({str(key or ""): str(value or "").strip() for key, value in row.items()})
    if not rows:
        raise ValueError("CSV must include at least one data row.")
    return headers, rows


def require_headers(headers: Iterable[str], required_headers: Iterable[str]) -> None:
    available = {str(header or "").strip() for header in headers}
    missing = [header for header in required_headers if header not in available]
    if missing:
        raise ValueError(f"Missing required CSV headers: {', '.join(missing)}")


def pick_first_non_empty(rows: list[dict[str, str]], key: str) -> str:
    for row in rows:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def parse_bool(value: Any) -> bool | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def parse_int(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def parse_float(value: Any) -> float | None:
    amount = parse_decimal_money(value)
    if amount is None:
        return None
    try:
        return float(amount)
    except (TypeError, ValueError):
        return None


def split_tokens(value: Any, *, sep: str = ",") -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for token in text.split(sep):
        stripped = token.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        out.append(stripped)
    return out


def split_image_lines(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for token in text.splitlines():
        stripped = token.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        out.append(stripped)
    return out


def weight_to_grams(value: Any, *, source_weight_unit: str) -> Decimal | None:
    parsed = parse_decimal_money(value)
    if parsed is None:
        return None
    unit = str(source_weight_unit or "").strip().lower()
    if unit == "kg":
        return parsed * Decimal("1000")
    if unit == "lb":
        return parsed * Decimal("453.59237")
    if unit == "oz":
        return parsed * Decimal("28.349523125")
    return parsed


def price_from_amount(amount: float | None, currency: str | None = "USD") -> Price | None:
    if amount is None:
        return None
    parsed = parse_decimal_money(amount)
    if parsed is None:
        return None
    currency_value = str(currency or "").strip().upper() or None
    return Price(current=Money(amount=parsed, currency=currency_value))


def media_from_urls(urls: list[str], *, variant_sku: str | None = None) -> list[Media]:
    media: list[Media] = []
    seen: set[str] = set()
    for index, url in enumerate(urls, start=1):
        normalized = str(url or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        media.append(
            Media(
                url=normalized,
                type="image",
                position=index,
                is_primary=(index == 1),
                variant_skus=([variant_sku] if variant_sku else []),
            )
        )
    return media


def ensure_product_defaults(product: Product) -> Product:
    if product.seo is None:
        product.seo = Seo()
    if product.source is None:
        product.source = SourceRef(platform="unknown")
    if product.taxonomy is None:
        product.taxonomy = CategorySet()
    if product.identifiers is None:
        product.identifiers = Identifiers()
    return product


def header_token(header: str) -> str:
    return _HEADER_TOKEN_RE.sub("_", str(header or "").strip().lower()).strip("_")


def _set_identifier(target: Identifiers, *, key: str, value: str) -> None:
    if not key or not value:
        return
    if key in target.values:
        return
    target.values[key] = value


def apply_extra_product_fields(product: Product, row: dict[str, str], *, known_headers: set[str]) -> None:
    ensure_product_defaults(product)
    for header, raw in row.items():
        if header in known_headers:
            continue
        value = str(raw or "").strip()
        if not value:
            continue
        token = header_token(header)
        if token == "title":
            product.title = value
            continue
        if token == "description":
            product.description = value
            continue
        if token == "brand":
            product.brand = value
            continue
        if token == "vendor":
            product.vendor = value
            continue
        if token == "tags":
            product.tags = split_tokens(value)
            continue
        if token == "seo_title":
            product.seo.title = value
            continue
        if token == "seo_description":
            product.seo.description = value
            continue
        if token == "source_id":
            product.source.id = value
            continue
        if token == "source_slug":
            product.source.slug = value
            continue
        if token == "source_url":
            product.source.url = value
            continue
        if token == "requires_shipping":
            parsed = parse_bool(value)
            if parsed is not None:
                product.requires_shipping = parsed
                continue
        if token == "track_quantity":
            parsed = parse_bool(value)
            if parsed is not None:
                product.track_quantity = parsed
                continue
        if token == "is_digital":
            parsed = parse_bool(value)
            if parsed is not None:
                product.is_digital = parsed
                continue
        _set_identifier(product.identifiers, key=f"csv:{token}", value=value)


def apply_extra_variant_fields(variant: Variant, row: dict[str, str], *, known_headers: set[str]) -> None:
    if variant.identifiers is None:
        variant.identifiers = Identifiers()
    for header, raw in row.items():
        if header in known_headers:
            continue
        value = str(raw or "").strip()
        if not value:
            continue
        token = header_token(header)
        if token in {"variant_sku", "sku"} and not variant.sku:
            variant.sku = value
            continue
        if token in {"variant_title", "title"} and not variant.title:
            variant.title = value
            continue
        if token in {"variant_id", "id"} and not variant.id:
            variant.id = value
            continue
        if token in {"variant_inventory_qty", "inventory_quantity"}:
            qty = parse_int(value)
            if qty is not None:
                variant.inventory.quantity = qty
                variant.inventory.track_quantity = True
                variant.inventory.available = qty > 0
                continue
        if token in {"variant_available", "available"}:
            parsed = parse_bool(value)
            if parsed is not None:
                variant.inventory.available = parsed
                continue
        if token in {"variant_price", "price"} and variant.price is None:
            amount = parse_float(value)
            variant.price = price_from_amount(amount)
            continue
        _set_identifier(variant.identifiers, key=f"csv:{token}", value=value)


def parse_canonical_product_payload(payload: dict[str, Any]) -> Product:
    variants_payload = payload.get("variants")
    variants: list[Variant] = []
    if isinstance(variants_payload, list):
        for item in variants_payload:
            if isinstance(item, dict):
                variants.append(Variant(**item))

    product_payload = dict(payload)
    product_payload["variants"] = variants
    return Product(**product_payload)


def add_csv_provenance(
    product: Product,
    *,
    source_platform: str,
    detected_product_count: int,
    selected_product_key: str,
) -> None:
    provenance = dict(product.provenance or {})
    provenance["csv_import"] = {
        "source_platform": source_platform,
        "selection_policy": "first_product",
        "detected_product_count": detected_product_count,
        "selected_product_key": selected_product_key,
    }
    product.provenance = provenance


def option_defs_from_option_maps(option_maps: list[dict[str, str]]) -> list[OptionDef]:
    values_by_name: dict[str, list[str]] = {}
    for option_map in option_maps:
        for key, value in option_map.items():
            name = str(key or "").strip()
            token = str(value or "").strip()
            if not name or not token:
                continue
            values_by_name.setdefault(name, [])
            if token not in values_by_name[name]:
                values_by_name[name].append(token)
    return [OptionDef(name=name, values=values) for name, values in values_by_name.items()]


def tags_from_keywords(value: str) -> list[str]:
    return split_tokens(value, sep=",")


def taxonomy_from_primary(category: str | None) -> CategorySet:
    if not category:
        return CategorySet()
    parts = [token.strip() for token in str(category).split(">") if token.strip()]
    if not parts:
        parts = [str(category).strip()]
    return CategorySet(paths=[parts], primary=list(parts))


def weight_object(value_grams: Decimal | None) -> Weight | None:
    if value_grams is None:
        return None
    return Weight(value=value_grams, unit="g")
