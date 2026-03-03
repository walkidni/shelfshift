"""Product URL detection."""

import re
from urllib.parse import parse_qs, unquote, urlparse


_AMAZON_ASIN_RE = re.compile(r"/(?:gp/product|dp)/([A-Z0-9]{10})(?:[/?#]|$)", re.I)
_ALIEXPRESS_ITEM_RE = re.compile(r"/(?:item|i)/(\d+)\.html(?:[/?#]|$)", re.I)
_ALIEXPRESS_X_OBJECT_RE = re.compile(
    r"x_object_id(?:%25)?(?:%3A|%3D|:|=)(\d{12,20})",
    re.I,
)

_LOCALE_PREFIX_RE = r"(?:[a-z]{2}(?:-[a-z0-9]{2,8})?/)?"
_SHOPIFY_PRODUCT_RE = re.compile(
    rf"^/{_LOCALE_PREFIX_RE}(?:collections/[^/]+/)?products/([^/?#]+?)(?:\.(?:js|json))?/?$",
    re.I,
)
_WOOCOMMERCE_PRODUCT_RE = re.compile(
    rf"^/{_LOCALE_PREFIX_RE}product/([^/?#]+)/?$",
    re.I,
)
_WOOCOMMERCE_STORE_API_PRODUCT_RE = re.compile(
    r"^/wp-json/wc/store/v1/products/([^/?#]+)/?$",
    re.I,
)
_WOOCOMMERCE_API_RE = re.compile(r"^/wp-json/wc/(?:store/v1|v[1-9]+)/", re.I)
_SQUARESPACE_PRODUCT_RE = re.compile(r"^/(?:shop|store)/(?:p/)?([a-z0-9-]+)/?$", re.I)
_SQUARESPACE_SHOP_PATH_RE = re.compile(r"^/(?:shop|store)(?:/|$)", re.I)


def extract_shopify_slug_from_path(path: str) -> str | None:
    match = _SHOPIFY_PRODUCT_RE.search(path or "")
    if not match:
        return None
    return match.group(1)


def extract_woocommerce_store_api_product_token(path: str) -> str | None:
    match = _WOOCOMMERCE_STORE_API_PRODUCT_RE.search(path or "")
    if not match:
        return None
    return unquote(match.group(1))


def detect_product_url(url: str) -> dict:
    """
    Returns: {'platform', 'is_product', 'product_id', 'slug'}
    """
    res = {"platform": None, "is_product": False, "product_id": None, "slug": None}
    try:
        parsed = urlparse(url)
    except Exception:
        return res

    host = (parsed.netloc or "").lower()
    path = parsed.path or ""
    query = parse_qs(parsed.query)

    if "amazon." in host:
        match = _AMAZON_ASIN_RE.search(path)
        if match:
            res.update(platform="amazon", is_product=True, product_id=match.group(1))
            return res
        for key in ("asin", "ASIN"):
            values = query.get(key) or []
            if values and re.fullmatch(r"[A-Z0-9]{10}", values[0], re.I):
                res.update(platform="amazon", is_product=True, product_id=values[0])
                return res
        res.update(platform="amazon")
        return res

    if "aliexpress." in host:
        match = _ALIEXPRESS_ITEM_RE.search(path)
        if match:
            res.update(platform="aliexpress", is_product=True, product_id=match.group(1))
            return res
        res.update(platform="aliexpress")
        return res

    # Run Woo/Squarespace checks before Shopify fallback path checks to avoid
    # classifying other platforms as Shopify from generic /products paths.
    match = _WOOCOMMERCE_PRODUCT_RE.search(path)
    if match:
        res.update(platform="woocommerce", is_product=True, slug=match.group(1))
        return res
    product_values = query.get("product") or []
    if product_values and re.fullmatch(r"\d+", product_values[0]):
        res.update(platform="woocommerce", is_product=True, product_id=product_values[0])
        return res
    token = extract_woocommerce_store_api_product_token(path)
    if token:
        if re.fullmatch(r"\d+", token):
            res.update(platform="woocommerce", is_product=True, product_id=token)
        else:
            res.update(platform="woocommerce", is_product=True, slug=token)
        return res
    if _WOOCOMMERCE_API_RE.search(path):
        res.update(platform="woocommerce")
        return res

    match = _SQUARESPACE_PRODUCT_RE.search(path)
    if host.endswith(".squarespace.com") and match:
        res.update(platform="squarespace", is_product=True, slug=match.group(1))
        return res
    if host.endswith(".squarespace.com"):
        res.update(platform="squarespace")
        return res

    format_values = query.get("format") or []
    format_value = (format_values[0] if format_values else "").strip().lower()
    if format_value in {"json", "json-pretty"} and _SQUARESPACE_SHOP_PATH_RE.search(path):
        if match:
            res.update(platform="squarespace", is_product=True, slug=match.group(1))
            return res
        res.update(platform="squarespace")
        return res

    shopify_slug = extract_shopify_slug_from_path(path)
    if host.endswith(".myshopify.com") or shopify_slug:
        if shopify_slug:
            res.update(platform="shopify", is_product=True, slug=shopify_slug)
            return res
        res.update(platform="shopify")
        return res

    return res


__all__ = [
    "detect_product_url",
    "extract_shopify_slug_from_path",
    "extract_woocommerce_store_api_product_token",
]
