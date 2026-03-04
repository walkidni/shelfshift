from pathlib import Path

import pandas as pd
import pytest
from tests.helpers._csv_helpers import read_fixture_frame, read_frame

from shelfshift.core import export_csv, import_csv

_CSV_EXAMPLES_ROOT = Path(__file__).resolve().parents[2] / "csv_examples"

_ROUND_TRIP_CASES = [
    pytest.param("shopify.csv", "shopify", None, None, id="shopify"),
    pytest.param(
        "bigcommerce-modern.csv",
        "bigcommerce",
        "lb",
        {"bigcommerce_csv_format": "modern", "weight_unit": "lb"},
        id="bigcommerce-modern",
    ),
    pytest.param(
        "bigcommerce-legacy.csv",
        "bigcommerce",
        "lb",
        {"bigcommerce_csv_format": "legacy", "weight_unit": "lb"},
        id="bigcommerce-legacy",
    ),
    pytest.param("wix.csv", "wix", "lb", {"weight_unit": "lb"}, id="wix"),
    pytest.param(
        "squarespace.csv",
        "squarespace",
        "lb",
        {"weight_unit": "lb"},
        id="squarespace",
    ),
    pytest.param("woocommerce.csv", "woocommerce", None, None, id="woocommerce"),
]


@pytest.mark.parametrize(
    ("filename", "source_platform", "source_weight_unit", "export_options"),
    _ROUND_TRIP_CASES,
)
def test_csv_examples_round_trip_matches_original_csv(
    filename: str,
    source_platform: str,
    source_weight_unit: str | None,
    export_options: dict[str, str] | None,
) -> None:
    csv_path = _CSV_EXAMPLES_ROOT / filename

    imported = import_csv(
        csv_path,
        platform=source_platform,
        source_weight_unit=source_weight_unit,
    )
    exported = export_csv(
        imported.products,
        target=source_platform,
        options=export_options,
    )

    expected = read_fixture_frame(csv_path)
    actual = read_frame(exported.csv_bytes.decode("utf-8"))

    assert list(actual.columns) == list(expected.columns)
    pd.testing.assert_frame_equal(actual, expected)
