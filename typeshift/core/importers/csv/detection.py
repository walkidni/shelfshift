"""Auto-detect the source e-commerce platform from CSV headers."""


from .common import csv_rows, decode_csv_bytes

# Header fingerprints for auto-detection.
# Order matters: most specific signatures first to avoid false positives.
_PLATFORM_HEADER_SIGNATURES: list[tuple[str, set[str]]] = [
    ("squarespace", {"Title", "SKU", "Price", "Product Type [Non Editable]", "Visible"}),
    ("wix", {"handle", "fieldType", "name", "price", "sku"}),
    ("bigcommerce", {"Item", "SKU", "Name"}),              # modern format
    ("bigcommerce", {"Product Type", "Code", "Name"}),      # legacy format
    ("woocommerce", {"Type", "SKU", "Name", "Regular price"}),
    ("shopify", {"Handle", "Title", "Variant SKU", "Variant Price"}),
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
        "Unable to detect CSV platform from headers. "
        "Please select the source platform manually."
    )


__all__ = ["DETECTABLE_PLATFORMS", "detect_csv_platform"]
