# Shelfshift

Shelfshift is a Python toolkit for translating ecommerce catalogs across platforms.
It detects/imports product data from URL or CSV inputs, normalizes into a canonical model, and exports platform-specific CSV files.

## Installation

```bash
pip install shelfshift
```

Or with `uv`:

```bash
uv add shelfshift
uv sync
```

Quick smoke test:

```bash
python -c "import shelfshift; print(shelfshift.__version__)"
shelfshift --help
```

## Quick Start (CLI)

```bash
shelfshift convert ./source.csv --to shopify --out ./shopify.csv --report ./convert_report.json
```

Detect input kind/platform:

```bash
shelfshift detect ./source.csv
shelfshift detect "https://example.myshopify.com/products/demo-item"
```

## Quick Start (Library)

```python
from shelfshift import convert_csv

csv_bytes, report = convert_csv("./source.csv", target="shopify")
with open("./shopify.csv", "wb") as f:
    f.write(csv_bytes)
```

## Support

- Python: `>=3.10`
- URL detection: `shopify`, `woocommerce`, `squarespace`, `amazon`, `aliexpress`
- URL import: `shopify`, `woocommerce`, `squarespace`
- CSV import/export: `shopify`, `bigcommerce`, `wix`, `squarespace`, `woocommerce`

## Documentation

- Start here: `guides/INDEX.md`
- Library guides: `guides/library/INDEX.md`
- CLI guides: `guides/cli/INDEX.md`

## Development Note

For repeated local CLI work, activate `.venv` and run commands directly:

```bash
source .venv/bin/activate
shelfshift --help
```

## License

MIT. See `LICENSE`.
