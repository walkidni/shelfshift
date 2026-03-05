from pathlib import Path

import pandas as pd
import pytest
from tests.helpers._csv_helpers import read_fixture_frame, read_frame

from shelfshift.core import convert_csv

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


def _normalized_tag_tokens(value: str) -> list[str]:
    return sorted([token.strip() for token in str(value or "").split(",") if token.strip()])


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

    converted_csv_bytes, _report = convert_csv(
        csv_path,
        target=source_platform,
        source=source_platform,
        source_weight_unit=source_weight_unit,
        export_options=export_options,
    )

    expected = read_fixture_frame(csv_path)
    actual = read_frame(converted_csv_bytes.decode("utf-8"))

    assert list(actual.columns) == list(expected.columns)
    if source_platform == "shopify" and "Tags" in expected.columns:
        non_tag_columns = [column for column in expected.columns if column != "Tags"]
        pd.testing.assert_frame_equal(actual[non_tag_columns], expected[non_tag_columns])

        actual_tags = actual["Tags"].map(_normalized_tag_tokens).tolist()
        expected_tags = expected["Tags"].map(_normalized_tag_tokens).tolist()
        assert actual_tags == expected_tags
        return

    pd.testing.assert_frame_equal(actual, expected)
