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
- `shelfshift.server`: self-hosted FastAPI API surface
- Web UI: demo interface for core/server capabilities, not the primary target

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
- Server runner: `shelfshift-server`

## Supported Inputs

### URL import sources

- Shopify product URLs
- WooCommerce product/store API URLs
- Squarespace product URLs
- Amazon product URLs (requires `RAPIDAPI_KEY`)
- AliExpress product URLs (requires `RAPIDAPI_KEY`)

### CSV import sources

- Shopify
- BigCommerce
- Wix
- Squarespace
- WooCommerce

## Compatibility

- Python: `>=3.13`
- URL imports: `shopify`, `woocommerce`, `squarespace`, `amazon`, `aliexpress`
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
shelfshift-server --help
```

## Running Commands

Use one of the following workflows for CLI and server commands:

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

## Self-Hosted API (FastAPI)

Start server:

```bash
shelfshift-server
```

or:

```bash
uvicorn shelfshift.server.main:app --reload
```

Open:

- Swagger UI: `http://127.0.0.1:8000/docs`
- Landing page: `http://127.0.0.1:8000/`
- URL demo UI: `http://127.0.0.1:8000/url`
- CSV demo UI: `http://127.0.0.1:8000/csv`

### API Routes

- `GET /health`
- `GET /api/v1/detect`
- `POST /api/v1/import`
- `POST /api/v1/detect/csv`
- `POST /api/v1/import/csv`
- `POST /api/v1/export/from-product.csv`
- `POST /api/v1/export/shopify.csv`
- `POST /api/v1/export/bigcommerce.csv`
- `POST /api/v1/export/wix.csv`
- `POST /api/v1/export/squarespace.csv`
- `POST /api/v1/export/woocommerce.csv`

## API Examples

Detect URL:

```bash
curl "http://127.0.0.1:8000/api/v1/detect?url=https://example.myshopify.com/products/demo-item"
```

Import URL(s):

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/import" \
  -H "Content-Type: application/json" \
  -d '{"product_urls": ["https://example.myshopify.com/products/demo-item"]}'
```

Import CSV:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/import/csv" \
  -F "source_platform=shopify" \
  -F "file=@./source.csv"
```

For `bigcommerce`, `wix`, and `squarespace` source CSVs, include `source_weight_unit` (`g|kg|lb|oz`):

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/import/csv" \
  -F "source_platform=squarespace" \
  -F "source_weight_unit=kg" \
  -F "file=@./source.csv"
```

Export from canonical payload:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/export/from-product.csv" \
  -H "Content-Type: application/json" \
  -d '{"product": {"source": {"platform": "shopify"}, "title": "Demo"}, "target_platform": "shopify"}' \
  -o out.csv
```

## Canonical Model

All importers normalize into the Shelfshift canonical entities under:

- `shelfshift.core.canonical.entities`
- `shelfshift.core.canonical.serialization`

This canonical layer is the contract between import and export stages.

## Extensibility

Registry hooks are available via:

- `shelfshift.core.register_importer`
- `shelfshift.core.register_exporter`
- `shelfshift.core.list_importers`
- `shelfshift.core.list_exporters`

Use these for custom importer/exporter integration in internal tooling.

## Environment Variables

- `APP_NAME`: server/web title
- `APP_TAGLINE`: server/web subtitle
- `BRAND_PRIMARY`: UI primary color
- `BRAND_SECONDARY`: UI secondary color
- `BRAND_INK`: UI text color
- `DEBUG`: include/exclude `raw` in API import responses
- `LOG_VERBOSITY`: `low | medium | high | extrahigh`
- `RAPIDAPI_KEY`: required for Amazon/AliExpress URL imports
- `CORS_ALLOW_ORIGINS`: comma-separated CORS allowlist

## License

This project is licensed under the MIT License. See `LICENSE`.
