"""Command-line frontend for the Typeshift core engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from typeshift.core import (
    convert_csv,
    detect_csv,
    detect_url,
    export_csv,
    import_csv,
    import_url,
    parse_product_payload,
    validate,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _json_dump(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _cmd_detect_url(args: argparse.Namespace) -> int:
    _json_dump(detect_url(args.input).__dict__)
    return 0


def _cmd_detect_csv(args: argparse.Namespace) -> int:
    _json_dump(detect_csv(args.input).__dict__)
    return 0


def _cmd_import_url(args: argparse.Namespace) -> int:
    result = import_url(
        args.url,
        strict=args.strict,
        rapidapi_key=args.rapidapi_key,
    )
    _json_dump(
        {
            "products": [p.to_dict(include_raw=args.include_raw) for p in result.products],
            "errors": result.errors,
        }
    )
    return 0


def _cmd_import_csv(args: argparse.Namespace) -> int:
    result = import_csv(
        args.input,
        platform=args.source_platform,
        strict=args.strict,
        source_weight_unit=args.source_weight_unit,
    )
    _json_dump(
        {
            "products": [p.to_dict(include_raw=args.include_raw) for p in result.products],
            "errors": result.errors,
        }
    )
    return 0


def _cmd_convert(args: argparse.Namespace) -> int:
    csv_bytes, report = convert_csv(
        args.input,
        target=args.to,
        source=args.source,
        strict=args.strict,
        source_weight_unit=args.source_weight_unit,
        export_options={"weight_unit": args.weight_unit},
    )
    out_path = Path(args.out)
    out_path.write_bytes(csv_bytes)
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _json_dump({"output": str(out_path), "report": report})
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    result = import_csv(
        args.input,
        platform=args.platform,
        strict=args.strict,
        source_weight_unit=args.source_weight_unit,
    )
    reports = validate(result.products)
    payload = [
        {
            "valid": report.valid,
            "issues": [issue.__dict__ for issue in report.issues],
        }
        for report in reports
    ]
    if args.report:
        Path(args.report).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _json_dump(payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="typeshift", description="Typeshift core engine CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect = subparsers.add_parser("detect", help="Detect input kind/platform from URL or CSV path")
    detect.add_argument("input", help="URL or CSV file path")
    detect.set_defaults(func=lambda args: _cmd_detect_csv(args) if Path(args.input).exists() else _cmd_detect_url(args))

    import_url_cmd = subparsers.add_parser("import-url", help="Import canonical products from one or more URLs")
    import_url_cmd.add_argument("url", nargs="+", help="One or more product URLs")
    import_url_cmd.add_argument("--rapidapi-key", default=None)
    import_url_cmd.add_argument("--include-raw", action="store_true")
    import_url_cmd.add_argument("--strict", action="store_true")
    import_url_cmd.set_defaults(func=lambda args: _cmd_import_url(argparse.Namespace(**{**vars(args), "url": args.url if len(args.url) > 1 else args.url[0]})))

    convert = subparsers.add_parser("convert", help="Convert source CSV to target platform CSV")
    convert.add_argument("input", help="Source CSV file path")
    convert.add_argument("--to", required=True, choices=["shopify", "bigcommerce", "wix", "squarespace", "woocommerce"])
    convert.add_argument("--source", default=None)
    convert.add_argument("--source-weight-unit", default="")
    convert.add_argument("--weight-unit", default="")
    convert.add_argument("--strict", action="store_true")
    convert.add_argument("--out", required=True)
    convert.add_argument("--report", default="")
    convert.set_defaults(func=_cmd_convert)

    validate_cmd = subparsers.add_parser("validate", help="Validate canonicalized products imported from source CSV")
    validate_cmd.add_argument("input", help="Source CSV file path")
    validate_cmd.add_argument("--platform", default=None)
    validate_cmd.add_argument("--source-weight-unit", default="")
    validate_cmd.add_argument("--strict", action="store_true")
    validate_cmd.add_argument("--report", default="")
    validate_cmd.set_defaults(func=_cmd_validate)

    import_csv_cmd = subparsers.add_parser("import-csv", help="Import canonical products from source CSV")
    import_csv_cmd.add_argument("input", help="Source CSV file path")
    import_csv_cmd.add_argument("--source-platform", default=None)
    import_csv_cmd.add_argument("--source-weight-unit", default="")
    import_csv_cmd.add_argument("--include-raw", action="store_true")
    import_csv_cmd.add_argument("--strict", action="store_true")
    import_csv_cmd.set_defaults(func=_cmd_import_csv)

    export_csv_cmd = subparsers.add_parser("export-csv", help="Export canonical JSON payload to target CSV")
    export_csv_cmd.add_argument("input", help="Canonical product JSON path")
    export_csv_cmd.add_argument("--to", required=True, choices=["shopify", "bigcommerce", "wix", "squarespace", "woocommerce"])
    export_csv_cmd.add_argument("--weight-unit", default="")
    export_csv_cmd.add_argument("--out", required=True)
    export_csv_cmd.add_argument("--report", default="")
    export_csv_cmd.set_defaults(func=_cmd_export_csv)

    return parser


def _cmd_export_csv(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    products = parse_product_payload(payload)

    exported = export_csv(
        products,
        target=args.to,
        options={"weight_unit": args.weight_unit},
    )
    Path(args.out).write_bytes(exported.csv_bytes)
    report = {"filename": exported.filename, "target_platform": args.to}
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _json_dump({"output": args.out, "report": report})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        parser.exit(status=2, message=f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
