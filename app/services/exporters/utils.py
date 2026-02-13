import csv
import io
from datetime import datetime, timezone
import re
from typing import Iterable

from app.models import Product, Variant

_SAFE_DEST_RE = re.compile(r"[^a-z0-9-]+")


def ordered_unique(items: Iterable[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = (item or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        values.append(cleaned)
    return values


def format_number(value: float | None, *, decimals: int) -> str:
    if value is None:
        return ""
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")


def dict_rows_to_csv(rows: list[dict[str, str]], columns: list[str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp_compact(now: datetime | None = None) -> str:
    dt = now or _utcnow()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def make_export_filename(destination: str, *, now: datetime | None = None) -> str:
    cleaned = (destination or "").strip().lower().replace("_", "-")
    cleaned = _SAFE_DEST_RE.sub("-", cleaned).strip("-")
    if not cleaned:
        cleaned = "export"
    return f"{cleaned}-{utc_timestamp_compact(now)}.csv"


def resolve_variants(product: Product) -> list[Variant]:
    variants = list(product.variants or [])
    if variants:
        return variants

    default_price = None
    if isinstance(product.price, dict) and isinstance(product.price.get("amount"), (int, float)):
        default_price = float(product.price["amount"])

    return [Variant(id=product.id, price_amount=default_price, weight=product.weight)]
