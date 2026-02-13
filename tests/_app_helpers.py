from typing import Any

from app.models import ProductResult


def patch_run_import_product(
    monkeypatch: Any,
    *,
    expected_url: str,
    product: ProductResult,
) -> None:
    def fake_run_import_product(product_url: str) -> ProductResult:
        assert product_url == expected_url
        return product

    monkeypatch.setattr("app.main._run_import_product", fake_run_import_product)
