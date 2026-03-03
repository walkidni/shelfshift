from datetime import datetime, timezone
import sys
from pathlib import Path

import pytest

# Ensure imports resolve from `src/` when running `pytest` directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


@pytest.fixture(autouse=True)
def _freeze_export_filename_timestamp(monkeypatch) -> None:
    fixed_now = datetime(2026, 2, 8, 0, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("shelfshift.core.exporters.shared.utils._utcnow", lambda: fixed_now)
