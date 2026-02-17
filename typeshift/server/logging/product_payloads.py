from typing import Any

from babel.numbers import get_currency_symbol

from ...core.canonical.entities import Product
from ..config import get_settings

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
    seo = data.get("seo") if isinstance(data.get("seo"), dict) else {}
    if isinstance(seo, dict):
        seo["description"] = _truncate_description(seo.get("description"), limit=limit)
        data["seo"] = seo


def _build_normal_variants(variants: list[dict[str, Any]], *, currency: str | None) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        option_values = variant.get("option_values") if isinstance(variant.get("option_values"), list) else []
        option_map: dict[str, str] = {}
        for item in option_values:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            value = str(item.get("value") or "").strip()
            if not name or not value:
                continue
            option_map[name] = value

        price_payload = variant.get("price") if isinstance(variant.get("price"), dict) else {}
        current_payload = price_payload.get("current") if isinstance(price_payload.get("current"), dict) else {}
        amount = current_payload.get("amount")
        variant_currency = str(current_payload.get("currency") or currency or "").strip() or None
        media = variant.get("media") if isinstance(variant.get("media"), list) else []
        output.append(
            {
                "options": option_map,
                "price": _format_price(amount, variant_currency),
                "has_image": any(
                    isinstance(item, dict)
                    and str(item.get("type") or "").strip().lower() == "image"
                    and bool(str(item.get("url") or "").strip())
                    for item in media
                ),
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
    current_payload = price_payload.get("current") if isinstance(price_payload.get("current"), dict) else {}
    amount = current_payload.get("amount")
    currency = str(current_payload.get("currency") or "").strip() or None
    variants = data.get("variants") if isinstance(data.get("variants"), list) else []
    source = data.get("source") if isinstance(data.get("source"), dict) else {}
    taxonomy = data.get("taxonomy") if isinstance(data.get("taxonomy"), dict) else {}
    taxonomy_primary = taxonomy.get("primary") if isinstance(taxonomy.get("primary"), list) else []
    category = " > ".join(str(item).strip() for item in taxonomy_primary if str(item).strip())
    media = data.get("media") if isinstance(data.get("media"), list) else []
    image_count = sum(
        1
        for item in media
        if isinstance(item, dict)
        and str(item.get("type") or "").strip().lower() == "image"
        and bool(str(item.get("url") or "").strip())
    )

    summary = {
        "platform": source.get("platform"),
        "title": data.get("title"),
        "description": _truncate_description(data.get("description"), limit=_DEFAULT_DESCRIPTION_LIMITS["medium"]),
        "meta_description": _truncate_description(
            (data.get("seo") or {}).get("description") if isinstance(data.get("seo"), dict) else None,
            limit=_DEFAULT_DESCRIPTION_LIMITS["medium"],
        ),
        "brand": data.get("brand"),
        "category": category,
        "vendor": data.get("vendor"),
        "price": _format_price(amount, currency),
        "options": data.get("options") if isinstance(data.get("options"), list) else [],
        "images": {"count": image_count},
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
