from datetime import datetime, timezone
import sys
from pathlib import Path

import pytest

# Ensure `import app` works when running `pytest` without needing PYTHONPATH hacks.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _freeze_export_filename_timestamp(monkeypatch) -> None:
    fixed_now = datetime(2026, 2, 8, 0, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("typeshift.core.exporters.shared.utils._utcnow", lambda: fixed_now)
