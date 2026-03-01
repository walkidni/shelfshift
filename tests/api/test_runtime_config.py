from __future__ import annotations

from fastapi.testclient import TestClient

from shelfshift.server.helpers import importing as importing_helpers
from shelfshift.server.main import create_app
from shelfshift.server.config import Settings
from tests.helpers._model_builders import Product


def _settings(**overrides) -> Settings:
    base = Settings(
        app_name="ShelfShift Injected",
        app_tagline="Injected tagline",
        brand_primary="#111111",
        brand_secondary="#222222",
        brand_ink="#333333",
        debug=False,
        log_verbosity="medium",
        rapidapi_key=None,
        cors_allow_origins=("https://example.test",),
    )
    data = {**base.__dict__, **overrides}
    return Settings(**data)


def _sample_product() -> Product:
    return Product(
        platform="shopify",
        id="prod-1",
        title="Demo Mug",
        description="Demo description",
        price={"amount": 12.0, "currency": "USD"},
        images=[],
        options={},
        variants=[],
        raw={"source": "payload"},
    )


def test_create_app_accepts_injected_settings_and_uses_app_and_cors() -> None:
    app = create_app(
        settings=_settings(
            app_name="Injected App",
            cors_allow_origins=("https://allowed.test",),
        )
    )
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["app"] == "Injected App"
    assert app.title == "Injected App"

    preflight = client.options(
        "/health",
        headers={
            "Origin": "https://allowed.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "https://allowed.test"


def test_create_app_injected_debug_controls_raw_payload(monkeypatch) -> None:
    product = _sample_product()

    def fake_run_import_product(product_url: str, *, settings: Settings):
        assert settings.debug is True
        assert product_url == "https://demo.myshopify.com/products/mug"
        return product

    monkeypatch.setattr(importing_helpers, "run_import_product", fake_run_import_product)

    app = create_app(settings=_settings(debug=True))
    client = TestClient(app)
    response = client.post(
        "/api/v1/import",
        json={"product_url": "https://demo.myshopify.com/products/mug"},
    )

    assert response.status_code == 200
    assert response.json().get("raw") == {"source": "payload"}


def test_run_import_product_uses_settings_for_logging(monkeypatch) -> None:
    product = _sample_product()
    captured: dict[str, object] = {}

    monkeypatch.setattr(importing_helpers, "fetch_product_details", lambda *_args, **_kwargs: product)

    def fake_loggable(_product, *, verbosity=None, debug_enabled=None):
        captured["verbosity"] = verbosity
        captured["debug_enabled"] = debug_enabled
        return {"title": "ok"}

    monkeypatch.setattr(importing_helpers, "product_result_to_loggable", fake_loggable)

    result = importing_helpers.run_import_product(
        "https://demo.myshopify.com/products/mug",
        settings=_settings(debug=True, log_verbosity="high"),
    )

    assert result.title == "Demo Mug"
    assert captured == {"verbosity": "high", "debug_enabled": True}


def test_injected_settings_override_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "Env Name")
    app = create_app(settings=_settings(app_name="Injected Name"))
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["app"] == "Injected Name"


def test_default_create_app_uses_current_env_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "Env App One")
    app_one = create_app()
    client_one = TestClient(app_one)
    assert client_one.get("/health").json()["app"] == "Env App One"

    monkeypatch.setenv("APP_NAME", "Env App Two")
    app_two = create_app()
    client_two = TestClient(app_two)
    assert client_two.get("/health").json()["app"] == "Env App Two"
