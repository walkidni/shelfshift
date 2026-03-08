"""Auto-detect the source e-commerce platform from CSV headers."""

from ...csv_schemas.bigcommerce import (
    BIGCOMMERCE_LEGACY_DETECTION_HEADERS,
    BIGCOMMERCE_MODERN_DETECTION_HEADERS,
)
from ...csv_schemas.shopify import SHOPIFY_DETECTION_HEADERS_NEW, SHOPIFY_REQUIRED_HEADERS_OLD
from ...csv_schemas.squarespace import SQUARESPACE_REQUIRED_HEADERS
from ...csv_schemas.wix import WIX_REQUIRED_HEADERS
from ...csv_schemas.woocommerce import WOOCOMMERCE_REQUIRED_HEADERS
from .common import csv_rows, decode_csv_bytes

# Header fingerprints for auto-detection.
# Order matters: most specific signatures first to avoid false positives.
_PLATFORM_HEADER_SIGNATURES: list[tuple[str, set[str]]] = [
    ("squarespace", set(SQUARESPACE_REQUIRED_HEADERS)),
    ("wix", set(WIX_REQUIRED_HEADERS)),
    ("bigcommerce", set(BIGCOMMERCE_MODERN_DETECTION_HEADERS)),
    ("bigcommerce", set(BIGCOMMERCE_LEGACY_DETECTION_HEADERS)),
    ("woocommerce", set(WOOCOMMERCE_REQUIRED_HEADERS)),
    ("shopify", set(SHOPIFY_DETECTION_HEADERS_NEW)),
    ("shopify", set(SHOPIFY_REQUIRED_HEADERS_OLD)),
]

DETECTABLE_PLATFORMS = ("shopify", "bigcommerce", "wix", "squarespace", "woocommerce")


def detect_csv_platform(csv_bytes: bytes) -> str:
    """Inspect CSV headers and return the detected platform name.

    Raises ``ValueError`` when no known platform matches.
    """
    csv_text = decode_csv_bytes(csv_bytes)
    headers, _ = csv_rows(csv_text)
    header_set = set(headers)
    for platform, signature in _PLATFORM_HEADER_SIGNATURES:
        if signature.issubset(header_set):
            return platform
    raise ValueError(
        "Unable to detect CSV platform from headers. Please select the source platform manually."
    )


__all__ = ["DETECTABLE_PLATFORMS", "detect_csv_platform"]
