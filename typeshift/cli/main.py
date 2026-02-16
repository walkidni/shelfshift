"""Command-line frontend for the Typeshift core engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from typeshift.core import (
    detect_csv_platform,
    detect_product_url,
    import_product_from_csv,
    import_product_from_url,
)


def _json_dump(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _cmd_detect_url(args: argparse.Namespace) -> int:
    _json_dump(detect_product_url(args.url))
    return 0


def _cmd_detect_csv(args: argparse.Namespace) -> int:
    csv_bytes = Path(args.file).read_bytes()
    _json_dump({"platform": detect_csv_platform(csv_bytes)})
    return 0


def _cmd_import_url(args: argparse.Namespace) -> int:
    product = import_product_from_url(args.url, rapidapi_key=args.rapidapi_key)
    _json_dump(product.to_dict(include_raw=args.include_raw))
    return 0


def _cmd_import_csv(args: argparse.Namespace) -> int:
    csv_bytes = Path(args.file).read_bytes()
    product = import_product_from_csv(
        source_platform=args.source_platform,
        csv_bytes=csv_bytes,
        source_weight_unit=args.source_weight_unit,
    )
    _json_dump(product.to_dict(include_raw=args.include_raw))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="typeshift", description="Typeshift core engine CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_url = subparsers.add_parser("detect-url", help="Detect product URL platform")
    detect_url.add_argument("url")
    detect_url.set_defaults(func=_cmd_detect_url)

    detect_csv = subparsers.add_parser("detect-csv", help="Detect source platform from CSV headers")
    detect_csv.add_argument("file", help="Path to source CSV")
    detect_csv.set_defaults(func=_cmd_detect_csv)

    import_url = subparsers.add_parser("import-url", help="Import canonical product from URL")
    import_url.add_argument("url")
    import_url.add_argument("--rapidapi-key", default=None)
    import_url.add_argument("--include-raw", action="store_true")
    import_url.set_defaults(func=_cmd_import_url)

    import_csv = subparsers.add_parser("import-csv", help="Import canonical product from source CSV")
    import_csv.add_argument("--source-platform", required=True)
    import_csv.add_argument("--file", required=True, help="Path to source CSV")
    import_csv.add_argument("--source-weight-unit", default="")
    import_csv.add_argument("--include-raw", action="store_true")
    import_csv.set_defaults(func=_cmd_import_csv)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        parser.exit(status=2, message=f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
