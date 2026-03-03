# Shelfshift CLI Core Concepts

## Command Overview

Available commands:

- `detect`
- `import-url`
- `import-csv`
- `convert`
- `validate`
- `export-csv`

Most commands print JSON to stdout.

## When to Use What

| Situation | Command |
| --- | --- |
| Detect source platform/type | `detect` |
| Import product URL(s) to canonical JSON | `import-url` |
| Import source CSV to canonical JSON | `import-csv` |
| Convert source CSV directly to target CSV | `convert` |
| Run canonical validation from CSV input | `validate` |
| Export canonical JSON to target CSV | `export-csv` |

## Canonical Envelope Format

`import-url` and `import-csv` output an envelope:

```json
{
  "products": [/* canonical product objects */],
  "errors": [/* batch errors, if any */]
}
```

`export-csv` expects canonical product object(s), not the full envelope. Use only the `products` array.

## Supported Platform Values

- URL import sources: `shopify`, `woocommerce`, `squarespace`
- URL detection platforms: `shopify`, `woocommerce`, `squarespace`, `amazon`, `aliexpress`
- CSV import sources: `shopify`, `bigcommerce`, `wix`, `squarespace`, `woocommerce`
- CSV export targets: `shopify`, `bigcommerce`, `wix`, `squarespace`, `woocommerce`

## Exit Codes

- `0`: success
- `2`: command failed (argument error or runtime error)

---

Previous: [CLI Getting Started](./GETTING_STARTED.md) | Next: [CLI Command Reference](./COMMAND_REFERENCE.md)
