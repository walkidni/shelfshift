from __future__ import annotations

from shelfshift.core import api as core_api
from shelfshift.core.importers import url as url_importers
from tests.helpers._model_builders import Product


_AMAZON_URL = "https://www.amazon.com/dp/B0C1234567"


def _sample_product() -> Product:
    return Product(
        platform="amazon",
        id="B0C1234567",
        title="Demo Product",
        description="Demo",
        price={"amount": 10.0, "currency": "USD"},
        images=[],
        options={},
        variants=[],
        raw={},
    )


def test_import_product_from_url_prefers_explicit_rapidapi_key(monkeypatch) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "env-key")
    captured: dict[str, str | None] = {}

    def fake_fetch(_url, cfg):
        captured["rapidapi_key"] = cfg.rapidapi_key
        return _sample_product()

    monkeypatch.setattr(url_importers, "fetch_product_details", fake_fetch)

    result = url_importers.import_product_from_url(_AMAZON_URL, rapidapi_key="explicit-key")
    assert result.source.id == "B0C1234567"
    assert captured["rapidapi_key"] == "explicit-key"


def test_import_product_from_url_uses_env_rapidapi_key_when_explicit_missing(monkeypatch) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "env-key")
    captured: dict[str, str | None] = {}

    def fake_fetch(_url, cfg):
        captured["rapidapi_key"] = cfg.rapidapi_key
        return _sample_product()

    monkeypatch.setattr(url_importers, "fetch_product_details", fake_fetch)

    result = url_importers.import_product_from_url(_AMAZON_URL)
    assert result.source.id == "B0C1234567"
    assert captured["rapidapi_key"] == "env-key"


def test_import_product_from_url_errors_when_rapidapi_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("RAPIDAPI_KEY", raising=False)
    try:
        url_importers.import_product_from_url(_AMAZON_URL)
    except ValueError as exc:
        assert "RAPIDAPI_KEY is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError when RAPIDAPI_KEY is missing.")


def test_core_import_url_prefers_explicit_rapidapi_key(monkeypatch) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "env-key")
    captured: dict[str, str | None] = {}

    def fake_import_product_from_url(_url: str, *, rapidapi_key: str | None = None):
        captured["rapidapi_key"] = rapidapi_key
        return _sample_product()

    monkeypatch.setattr(core_api, "import_product_from_url", fake_import_product_from_url)

    result = core_api.import_url(_AMAZON_URL, rapidapi_key="explicit-key")
    assert len(result.products) == 1
    assert captured["rapidapi_key"] == "explicit-key"


def test_core_import_url_uses_env_rapidapi_key_when_explicit_missing(monkeypatch) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "env-key")
    captured: dict[str, str | None] = {}

    def fake_import_product_from_url(_url: str, *, rapidapi_key: str | None = None):
        captured["rapidapi_key"] = rapidapi_key
        return _sample_product()

    monkeypatch.setattr(core_api, "import_product_from_url", fake_import_product_from_url)

    result = core_api.import_url(_AMAZON_URL)
    assert len(result.products) == 1
    assert captured["rapidapi_key"] == "env-key"
