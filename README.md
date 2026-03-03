# Shelfshift

Shelfshift is a developer toolkit for ecommerce catalog translation.

Given a product source (URL or CSV), Shelfshift normalizes it into a canonical product model and exports platform-specific CSVs for:

- Shopify
- BigCommerce
- Wix
- Squarespace
- WooCommerce

This project is built for ecommerce developers and integration engineers who need reliable, automatable catalog pipelines.

## Positioning

- `shelfshift.core`: the primary product (importable Python library)
- `shelfshift` CLI: automation and local workflows

## Core Capabilities

- URL detection (`shopify`, `woocommerce`, `squarespace`, `amazon`, `aliexpress`)
- URL import to canonical product(s)
- CSV platform detection + CSV import to canonical product(s)
- Canonical product validation
- Canonical -> target-platform CSV export
- Single and batch export flows

## Package Surfaces

- Library: `shelfshift.core`
- CLI: `shelfshift` (entrypoint from `pyproject.toml`)

## Supported Inputs

### URL import sources

- Shopify product URLs
- WooCommerce product/store API URLs
- Squarespace product URLs

URL detection also classifies Amazon and AliExpress URLs, but URL importing is intentionally limited to the three sources above.

### CSV import sources

- Shopify
- BigCommerce
- Wix
- Squarespace
- WooCommerce

## Compatibility

- Python: `>=3.10`
- URL imports: `shopify`, `woocommerce`, `squarespace`
- CSV imports: `shopify`, `bigcommerce`, `wix`, `squarespace`, `woocommerce`
- CSV exports: `shopify`, `bigcommerce`, `wix`, `squarespace`, `woocommerce`

## Installation

### From PyPI (recommended for users)

```bash
pip install shelfshift
```

Or with `uv` in a project:

```bash
uv add shelfshift
uv sync
```

Quick smoke test:

```bash
python -c "import shelfshift, shelfshift.core; print(shelfshift.__version__)"
shelfshift --help
```

## Running Commands

Use one of the following workflows for CLI commands:

1. One-off invocation with `uv run`:

```bash
uv run shelfshift detect ./source.csv
```

2. Activate `.venv` and run commands directly (recommended for repeated local development):

```bash
source .venv/bin/activate
shelfshift detect ./source.csv
```

When `.venv` is activated, you do not need `uv run` prefixes.

Optional local env file:

```bash
cp .env.example .env
```

## Quick Start (Library)

```python
from shelfshift.core import import_url, export_csv

# 1) Import canonical product from URL
result = import_url("https://example.myshopify.com/products/demo-item")
product = result.products[0]

# 2) Export to target platform CSV
exported = export_csv(product, target="shopify", options={"publish": False, "weight_unit": "g"})
with open("product.csv", "wb") as f:
    f.write(exported.csv_bytes)
```

Batch URL import:

```python
from shelfshift.core import import_url

result = import_url([
    "https://store-a.com/products/a",
    "https://store-b.com/products/b",
])

# result.products and result.errors support partial-success workflows
print(len(result.products), len(result.errors))
```

## Quick Start (CLI)

Detect URL or CSV input:

```bash
shelfshift detect "https://example.myshopify.com/products/demo-item"
shelfshift detect ./source.csv
```

Import URL(s) to canonical JSON:

```bash
shelfshift import-url "https://example.myshopify.com/products/demo-item"
shelfshift import-url "https://store-a.com/products/a" "https://store-b.com/products/b"
```

Import source CSV to canonical JSON:

```bash
shelfshift import-csv ./source.csv --source-platform shopify
```

For `bigcommerce`, `wix`, and `squarespace` source CSVs, also pass `--source-weight-unit`:

```bash
shelfshift import-csv ./source.csv --source-platform squarespace --source-weight-unit kg
```

Convert source CSV directly to target CSV:

```bash
shelfshift convert ./source.csv --to shopify --out ./converted.csv --report ./report.json
```

If the source CSV platform is `bigcommerce`, `wix`, or `squarespace`, include `--source-weight-unit`:

```bash
shelfshift convert ./source.csv --source squarespace --source-weight-unit kg --to shopify --out ./converted.csv
```

Validate canonicalized products from CSV:

```bash
shelfshift validate ./source.csv --platform shopify --report ./validate.json
```

For `bigcommerce`, `wix`, and `squarespace` source CSVs, include `--source-weight-unit`:

```bash
shelfshift validate ./source.csv --platform wix --source-weight-unit kg --report ./validate.json
```

Export canonical JSON payload to target CSV:

```bash
shelfshift export-csv ./canonical.json --to woocommerce --out ./woocommerce.csv
```

## Canonical Model

All importers normalize into the Shelfshift canonical entities under:

- `shelfshift.core.canonical.entities`
- `shelfshift.core.canonical.io`

This canonical layer is the contract between import and export stages.

## Extensibility

Registry hooks are available via:

- `shelfshift.core.registry.register_importer`
- `shelfshift.core.registry.register_exporter`
- `shelfshift.core.registry.list_importers`
- `shelfshift.core.registry.list_exporters`

Use these for custom importer/exporter integration in internal tooling.

## Runtime Configuration Precedence

Shelfshift resolves runtime settings in this order:

1. Explicit runtime input (library args, CLI flags).
2. Process environment (including values loaded from `.env`).
3. Built-in defaults.

Configuration is resolved per core call.

## Environment Variables

No environment variables are required for `shelfshift.core` or the CLI.

## License

This project is licensed under the MIT License. See `LICENSE`.
