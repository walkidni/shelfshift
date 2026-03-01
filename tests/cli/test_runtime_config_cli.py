from __future__ import annotations

from types import SimpleNamespace

from shelfshift.cli import main as cli_main


def test_cli_import_url_prefers_explicit_rapidapi_key(monkeypatch) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "env-key")
    captured: dict[str, str | None] = {}

    def fake_import_url(_urls, *, strict=False, rapidapi_key=None):
        captured["rapidapi_key"] = rapidapi_key
        return SimpleNamespace(products=[], errors=[])

    monkeypatch.setattr(cli_main, "import_url", fake_import_url)
    monkeypatch.setattr(cli_main, "_json_dump", lambda _data: None)

    exit_code = cli_main.main(
        ["import-url", "https://www.amazon.com/dp/B0C1234567", "--rapidapi-key", "explicit-key"]
    )
    assert exit_code == 0
    assert captured["rapidapi_key"] == "explicit-key"


def test_cli_import_url_uses_env_rapidapi_key_when_flag_missing(monkeypatch) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "env-key")
    captured: dict[str, str | None] = {}

    def fake_import_url(_urls, *, strict=False, rapidapi_key=None):
        captured["rapidapi_key"] = rapidapi_key
        return SimpleNamespace(products=[], errors=[])

    monkeypatch.setattr(cli_main, "import_url", fake_import_url)
    monkeypatch.setattr(cli_main, "_json_dump", lambda _data: None)

    exit_code = cli_main.main(["import-url", "https://www.amazon.com/dp/B0C1234567"])
    assert exit_code == 0
    assert captured["rapidapi_key"] == "env-key"
