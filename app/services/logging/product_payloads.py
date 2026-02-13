from typing import Any

from babel.numbers import get_currency_symbol

from ...config import get_settings
from app.models import Product

_DEFAULT_DESCRIPTION_LIMITS = {
    "low": 80,
    "medium": 160,
    "high": 240,
}
_SUPPORTED_VERBOSITIES = {"low", "medium", "high", "extrahigh"}


def _truncate_description(value: str | None, *, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}... [truncated]"


def _normalize_verbosity(verbosity: str) -> str:
    normalized = str(verbosity or "").strip().lower()
    if normalized in _SUPPORTED_VERBOSITIES:
        return normalized
    return "medium"


def _format_number(value: float | int | None) -> str:
    if value is None:
        return ""
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


def _format_price(value: Any, currency: str | None) -> str:
    amount: float | None = None
    if isinstance(value, (int, float)):
        amount = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                amount = float(stripped)
            except ValueError:
                return stripped
    if amount is None:
        return ""
    number = _format_number(amount)

    symbol = ""
    currency_code = str(currency or "").upper()
    if currency_code:
        try:
            symbol = get_currency_symbol(currency_code, locale="en_US")
        except Exception:
            symbol = currency_code

    if symbol:
        if symbol.isalpha():
            return f"{number} {symbol}"
        return f"{number}{symbol}"
    if currency:
        return f"{number} {currency}"
    return number


def _truncate_meta_description(data: dict[str, Any], *, limit: int) -> None:
    data["description"] = _truncate_description(data.get("description"), limit=limit)
    data["meta_description"] = _truncate_description(data.get("meta_description"), limit=limit)


def _build_normal_variants(variants: list[dict[str, Any]], *, currency: str | None) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        variant_currency = str(variant.get("currency") or currency or "").strip() or None
        output.append(
            {
                "options": variant.get("options") if isinstance(variant.get("options"), dict) else {},
                "price": _format_price(variant.get("price_amount"), variant_currency),
                "has_image": bool(str(variant.get("image") or "").strip()),
            }
        )
    return output


def product_result_to_loggable(
    product: Product,
    *,
    verbosity: str | None = None,
    debug_enabled: bool | None = None,
) -> dict[str, Any] | None:
    settings = get_settings()
    if debug_enabled is None:
        debug_enabled = settings.debug

    if not debug_enabled:
        return None

    resolved_verbosity = verbosity if verbosity is not None else settings.log_verbosity
    level = _normalize_verbosity(resolved_verbosity)
    if level == "extrahigh":
        return product.to_dict(include_raw=True)

    data = product.to_dict(include_raw=False)

    if level == "high":
        _truncate_meta_description(data, limit=_DEFAULT_DESCRIPTION_LIMITS["high"])
        return data

    price_payload = data.get("price") if isinstance(data.get("price"), dict) else {}
    amount = price_payload.get("amount")
    currency = str(price_payload.get("currency") or "").strip() or None
    variants = data.get("variants") if isinstance(data.get("variants"), list) else []

    summary = {
        "platform": data.get("platform"),
        "title": data.get("title"),
        "description": _truncate_description(data.get("description"), limit=_DEFAULT_DESCRIPTION_LIMITS["medium"]),
        "meta_description": _truncate_description(
            data.get("meta_description"),
            limit=_DEFAULT_DESCRIPTION_LIMITS["medium"],
        ),
        "brand": data.get("brand"),
        "category": data.get("category"),
        "vendor": data.get("vendor"),
        "price": _format_price(amount, currency),
        "options": data.get("options") if isinstance(data.get("options"), dict) else {},
        "images": {"count": len(data.get("images") or [])},
        "variants_count": len(variants),
        "variants": _build_normal_variants(variants, currency=currency),
    }

    if level == "low":
        return {
            "platform": summary.get("platform"),
            "title": summary.get("title"),
            "price": summary.get("price"),
            "images": summary.get("images"),
            "variants_count": summary.get("variants_count"),
            "brand": summary.get("brand"),
            "category": summary.get("category"),
        }

    return summary
