import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.models import (
    Identifiers,
    Money,
    Price,
    Product,
    SourceRef,
    Variant,
    normalize_currency,
    parse_decimal_money,
)


def http_session(timeout: int = 20) -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    # store desired default timeout on the session for convenience
    s.request_timeout = timeout  # type: ignore[attr-defined]
    return s


class ProductClient:
    platform: str = "generic"

    def fetch_product(self, url: str) -> Product:
        raise NotImplementedError


@dataclass
class ApiConfig:
    """
    Minimal configuration for RapidAPI-backed clients.
    Hosts/endpoints are hardcoded in the clients.
    """

    rapidapi_key: str | None = None
    amazon_country: str = "US"  # used by the Amazon provider


def dedupe(seq: Iterable[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for x in seq:
        if isinstance(x, str) and x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def parse_money_to_float(x: Any) -> float | None:
    parsed = parse_decimal_money(x)
    if parsed is None:
        return None
    try:
        return float(parsed)
    except (TypeError, ValueError):
        return None


def append_default_variant_if_empty(variants: list[Variant], default_variant: Variant | None) -> None:
    if variants or default_variant is None:
        return
    variants.append(default_variant)


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_JSON_LD_SCRIPT_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)


def strip_html(text: str) -> str:
    cleaned = _HTML_TAG_RE.sub(" ", text or "")
    return " ".join(cleaned.split())


def truncate(text: str, limit: int = 400) -> str:
    return (text or "")[:limit].strip()


def meta_from_description(
    title: str,
    description: str | None,
    *,
    strip_html_content: bool,
) -> tuple[str, str | None]:
    if not description:
        return title, None
    base = strip_html(description) if strip_html_content else description
    return title, truncate(base)


def to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return None


def pick_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def normalize_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped.startswith("//"):
        return f"https:{stripped}"
    return stripped


def slug_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")


def extract_names(items: Any, *, split_commas: bool = False) -> list[str]:
    names: list[str] = []
    if isinstance(items, str):
        tokens = items.split(",") if split_commas else [items]
        for token in tokens:
            stripped = token.strip()
            if stripped:
                names.append(stripped)
    elif isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    names.append(stripped)
                continue
            if not isinstance(item, dict):
                continue
            candidate = pick_name(item.get("value")) or pick_name(item.get("name")) or pick_name(item.get("title"))
            if candidate:
                names.append(candidate)
    return dedupe(names)


def extract_image_urls(
    items: Any,
    *,
    recursive: bool = False,
    dict_keys: tuple[str, ...] = ("url", "src"),
) -> list[str]:
    urls: list[str] = []
    if isinstance(items, str):
        normalized = normalize_url(items)
        if normalized:
            urls.append(normalized)
    elif isinstance(items, list):
        for item in items:
            if recursive:
                urls.extend(extract_image_urls(item, recursive=True, dict_keys=dict_keys))
                continue
            if isinstance(item, str):
                normalized = normalize_url(item)
            elif isinstance(item, dict):
                normalized = None
                for key in dict_keys:
                    normalized = normalize_url(item.get(key))
                    if normalized:
                        break
            else:
                normalized = None
            if normalized:
                urls.append(normalized)
    elif isinstance(items, dict):
        for key in dict_keys:
            normalized = normalize_url(items.get(key))
            if normalized:
                urls.append(normalized)
        if recursive:
            for key in ("image", "images", "items"):
                nested = items.get(key)
                if nested is not None:
                    urls.extend(extract_image_urls(nested, recursive=True, dict_keys=dict_keys))
    return dedupe(urls)


def _extract_json_ld_nodes(data: Any, *, target_type: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(data, dict):
        node_type = data.get("@type")
        if node_type == target_type or (isinstance(node_type, list) and target_type in node_type):
            out.append(data)
        graph = data.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                out.extend(_extract_json_ld_nodes(item, target_type=target_type))
    elif isinstance(data, list):
        for item in data:
            out.extend(_extract_json_ld_nodes(item, target_type=target_type))
    return out


def extract_product_json_ld_nodes(html: str) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for block in _JSON_LD_SCRIPT_RE.findall(html or ""):
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        products.extend(_extract_json_ld_nodes(data, target_type="Product"))
    return products


def _clean_identifier_values(values: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in values.items():
        key_str = str(key or "").strip()
        value_str = str(value or "").strip()
        if not key_str or not value_str:
            continue
        out[key_str] = value_str
    return out


def make_money(amount: Any, currency: Any) -> Money | None:
    parsed_amount = parse_decimal_money(amount)
    parsed_currency = normalize_currency(currency)
    if parsed_amount is None and parsed_currency is None:
        return None
    return Money(amount=parsed_amount, currency=parsed_currency)


def make_price(
    *,
    amount: Any,
    currency: Any,
    compare_at: Any = None,
    cost: Any = None,
    min_price: Any = None,
    max_price: Any = None,
) -> Price | None:
    current_money = make_money(amount, currency)
    if current_money is None:
        return None

    return Price(
        current=current_money,
        compare_at=make_money(compare_at, currency),
        cost=make_money(cost, currency),
        min_price=make_money(min_price, currency),
        max_price=make_money(max_price, currency),
    )


def make_identifiers(values: dict[str, Any]) -> Identifiers:
    cleaned = _clean_identifier_values(values)
    return Identifiers(values=cleaned)


def finalize_product_typed_fields(product: Product, *, source_url: str) -> Product:
    if product.source is None:
        product.source = SourceRef(
            platform="unknown",
            id=None,
            slug=None,
            url=source_url,
        )
    elif not product.source.url:
        product.source.url = source_url

    if product.taxonomy.primary is None and product.taxonomy.paths:
        product.taxonomy.primary = list(product.taxonomy.paths[0])
    return product
