from typing import Any

from typeshift.core.canonical import Product


def patch_run_import_product(
    monkeypatch: Any,
    *,
    expected_url: str,
    product: Product,
) -> None:
    def fake_run_import_product(product_url: str) -> Product:
        assert product_url == expected_url
        return product

    monkeypatch.setattr("typeshift.server.helpers.importing.run_import_product", fake_run_import_product)
