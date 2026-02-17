"""CSV-based importers."""


from app.models import Product
from app.services.csv_importers import import_product_from_csv as _import_product_from_csv
from app.services.csv_importers import import_products_from_csv as _import_products_from_csv


def import_product_from_csv(
    *,
    source_platform: str,
    csv_bytes: bytes,
    source_weight_unit: str | None = None,
) -> Product:
    return _import_product_from_csv(
        source_platform=source_platform,
        csv_bytes=csv_bytes,
        source_weight_unit=source_weight_unit,
    )


def import_products_from_csv(
    *,
    source_platform: str,
    csv_bytes: bytes,
    source_weight_unit: str | None = None,
) -> list[Product]:
    return _import_products_from_csv(
        source_platform=source_platform,
        csv_bytes=csv_bytes,
        source_weight_unit=source_weight_unit,
    )


__all__ = ["import_product_from_csv", "import_products_from_csv"]
