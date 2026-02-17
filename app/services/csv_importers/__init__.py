"""Compatibility facade for legacy ``app.services.csv_importers`` imports."""

from typeshift.core.importers.csv import (
    DETECTABLE_PLATFORMS,
    MAX_CSV_UPLOAD_BYTES,
    detect_csv_platform,
    import_product_from_csv,
    import_products_from_csv,
    parse_canonical_product_payload,
)

__all__ = [
    "DETECTABLE_PLATFORMS",
    "MAX_CSV_UPLOAD_BYTES",
    "detect_csv_platform",
    "import_product_from_csv",
    "import_products_from_csv",
    "parse_canonical_product_payload",
]
