from __future__ import annotations

import pytest
from types import SimpleNamespace

from shelfshift.cli import main as cli_main


def test_cli_import_url_passes_strict_only(monkeypatch) -> None:
    captured: dict[str, bool] = {}

    def fake_import_url(_urls, *, strict=False):
        captured["strict"] = strict
        return SimpleNamespace(products=[], errors=[])

    monkeypatch.setattr(cli_main, "import_url", fake_import_url)
    monkeypatch.setattr(cli_main, "_json_dump", lambda _data: None)

    exit_code = cli_main.main(["import-url", "https://demo.myshopify.com/products/demo", "--strict"])
    assert exit_code == 0
    assert captured["strict"] is True


def test_cli_import_url_rejects_removed_rapidapi_flag() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main(
            ["import-url", "https://www.amazon.com/dp/B0C1234567", "--rapidapi-key", "explicit-key"]
        )
    assert exc_info.value.code == 2
