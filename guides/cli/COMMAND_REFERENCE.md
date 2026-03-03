# Shelfshift CLI Command Reference

## `detect`

Behavior

- Detects platform/type for URL or CSV input.

Examples

```bash
shelfshift detect "https://example.myshopify.com/products/demo-item"
shelfshift detect ./source.csv
```

## `import-url`

Behavior

- Imports one or many product URLs to canonical JSON.
- `--strict` fails when one or more URLs fail.
- Detect can classify Amazon/AliExpress URLs, but URL import supports only Shopify, WooCommerce, and Squarespace product URLs.

Examples

```bash
shelfshift import-url "https://example.myshopify.com/products/demo-item"
```

```bash
shelfshift import-url \
  "https://store-a.com/products/a" \
  "https://store-b.com/products/b"
```

```bash
shelfshift import-url "https://store-a.com/products/a" --strict
```

## `import-csv`

Behavior

- Imports source CSV to canonical JSON.
- Auto-detects source platform unless `--source-platform` is provided.
- For `bigcommerce`, `wix`, and `squarespace`, pass `--source-weight-unit` when needed.

Examples

```bash
shelfshift import-csv ./source.csv
shelfshift import-csv ./source.csv --source-platform shopify
shelfshift import-csv ./source.csv --source-platform squarespace --source-weight-unit kg
```

## `convert`

Behavior

- Imports source CSV, canonicalizes it, then exports target CSV.

Examples

```bash
shelfshift convert ./source.csv \
  --to shopify \
  --out ./shopify.csv \
  --report ./convert_report.json
```

```bash
shelfshift convert ./source.csv \
  --source squarespace \
  --source-weight-unit kg \
  --to woocommerce \
  --weight-unit g \
  --out ./woocommerce.csv \
  --report ./convert_report.json
```

## `validate`

Behavior

- Imports CSV input and writes validation results.

Examples

```bash
shelfshift validate ./source.csv --platform shopify --report ./validate_report.json
shelfshift validate ./source.csv --platform wix --source-weight-unit lb --report ./validate_report.json
```

## `export-csv`

Behavior

- Exports canonical JSON payload (`dict` or `list[dict]`) to target CSV.

Example

```bash
shelfshift export-csv ./canonical_products.json \
  --to bigcommerce \
  --weight-unit g \
  --out ./bigcommerce.csv \
  --report ./export_report.json
```

---

Previous: [CLI Core Concepts](./CORE_CONCEPTS.md) | Next: [CLI Advanced Usage](./ADVANCED_USAGE.md)
