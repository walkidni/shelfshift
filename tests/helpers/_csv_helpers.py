import io
from pathlib import Path

import pandas as pd


def read_frame(csv_text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)


def read_fixture_frame(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)
