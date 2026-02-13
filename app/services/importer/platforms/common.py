import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.models import ProductResult, Variant


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

    def fetch_product(self, url: str) -> ProductResult:
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
    if x is None:
        return None
    if isinstance(x, (int, float)):
        try:
            return float(x)
        except Exception:
            return None
    if isinstance(x, str):
        s = x.strip()
        s = s.replace(",", "")
        s = re.sub(r"[^\d\.]", "", s)  # drop currency symbols/letters
        try:
            return float(s) if s else None
        except Exception:
            return None
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
