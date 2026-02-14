# Ecommerce Catalog Transfer

This app ingests supported ecommerce product URLs and returns CSV files that are importable into Shopify, BigCommerce, Wix, Squarespace, and WooCommerce.

Project surface:
- FastAPI API for programmatic use (`POST /api/v1/import`)
- CSV import API (`POST /api/v1/import/csv`)
- Canonical-to-CSV conversion API (`POST /api/v1/export/from-product.csv`)
- URL detection endpoint (`GET /api/v1/detect`)
- FastAPI CSV export endpoints:
  - `POST /api/v1/export/shopify.csv`
  - `POST /api/v1/export/bigcommerce.csv`
  - `POST /api/v1/export/wix.csv`
  - `POST /api/v1/export/squarespace.csv`
  - `POST /api/v1/export/woocommerce.csv`
- Simple web UI for one-step CSV export (`/`)
- Web CSV upload preview + conversion flow (`/import.csv` -> `/export-from-product.csv`)
- Shared importer services for Shopify, WooCommerce, Squarespace, Amazon, and AliExpress

## Supported import sources

- Shopify product URLs
- WooCommerce product URLs (storefront product URLs and Store API product URLs)
- Squarespace product URLs
- Amazon product URLs (requires `RAPIDAPI_KEY`)
- AliExpress item URLs (requires `RAPIDAPI_KEY`)

## URL detection coverage (`GET /api/v1/detect`)

- Shopify
- Amazon
- AliExpress
- WooCommerce
- Squarespace

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create local env config:

```bash
cp .env.example .env
```

4. Start the app:

```bash
uvicorn app.main:app --reload
```

5. Open:
- Web UI: `http://127.0.0.1:8000/`
- Swagger docs: `http://127.0.0.1:8000/docs`

## API usage

Detect URL platform:

```bash
curl "http://127.0.0.1:8000/api/v1/detect?url=https://example.myshopify.com/products/item"
```

Import product:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/import \
  -H "Content-Type: application/json" \
  -d '{"product_url":"https://example.myshopify.com/products/item"}'
```

Export Shopify CSV:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/export/shopify.csv" \
  -H "Content-Type: application/json" \
  -d '{"product_url":"https://example.myshopify.com/products/item","publish":false,"weight_unit":"g"}' \
  -o product.csv
```

Export Squarespace CSV:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/export/squarespace.csv" \
  -H "Content-Type: application/json" \
  -d '{"product_url":"https://example.myshopify.com/products/item","publish":false,"product_page":"shop","squarespace_product_url":"lemons","weight_unit":"kg"}' \
  -o product.csv
```

Export Wix CSV:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/export/wix.csv" \
  -H "Content-Type: application/json" \
  -d '{"product_url":"https://example.myshopify.com/products/item","publish":false,"weight_unit":"kg"}' \
  -o product.csv
```

Export WooCommerce CSV:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/export/woocommerce.csv" \
  -H "Content-Type: application/json" \
  -d '{"product_url":"https://example.myshopify.com/products/item","publish":false,"weight_unit":"kg"}' \
  -o product.csv
```

Export BigCommerce CSV:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/export/bigcommerce.csv" \
  -H "Content-Type: application/json" \
  -d '{"product_url":"https://example.myshopify.com/products/item","publish":false,"csv_format":"modern","weight_unit":"kg"}' \
  -o product.csv
```

Import source CSV into canonical product JSON:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/import/csv" \
  -F "source_platform=shopify" \
  -F "file=@./product.csv"
```

Export from canonical product JSON:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/export/from-product.csv" \
  -H "Content-Type: application/json" \
  -d '{"product":{...canonical product...},"target_platform":"woocommerce","publish":false}' \
  -o converted.csv
```

## Export request options

- Shopify: `publish`, `weight_unit` (`g`, `kg`, `lb`, `oz`)
- BigCommerce: `publish`, `csv_format` (`modern`, `legacy`), `weight_unit` (`g`, `kg`, `lb`, `oz`)
- Wix: `publish`, `weight_unit` (`kg`, `lb`)
- Squarespace: `publish`, `product_page`, `squarespace_product_url`, `weight_unit` (`kg`, `lb`)
- WooCommerce: `publish`, `weight_unit` (`kg`)

## Response behavior (`raw` field)

- Default (`DEBUG=false`): `raw` is omitted from response JSON.
- Debug mode (`DEBUG=true`): `raw` is included at product and variant level.

## Environment variables

- `APP_NAME`: app title in the UI
- `APP_TAGLINE`: subtitle shown in the UI hero section
- `BRAND_PRIMARY`: primary accent color
- `BRAND_SECONDARY`: secondary accent color
- `BRAND_INK`: main text color
- `DEBUG`: include/exclude `raw` payloads in responses
- `RAPIDAPI_KEY`: required for Amazon/AliExpress importers
- `AMAZON_COUNTRY`: fallback Amazon marketplace country code
- `CORS_ALLOW_ORIGINS`: comma-separated CORS allowlist

## Project layout

```text
app/
  main.py
  config.py
  schemas.py
  services/
    importer/
      __init__.py
      product_url_detection.py
      platforms/
        __init__.py
        common.py
        shopify.py
        squarespace.py
        woocommerce.py
        amazon.py
        aliexpress.py
    exporters/
      shopify_csv.py
      bigcommerce_csv.py
      wix_csv.py
      squarespace_csv.py
      woocommerce_csv.py
  web/
    templates/index.html
    static/styles.css
tests/
  api/
  exporters/
  importers/
  models/
  helpers/
  fixtures/
    exporter/<platform>/*.csv
    importers/<platform>/*
```

## Tests

```bash
pytest -q
```
