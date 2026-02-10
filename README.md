# Ecommerce Catalog Transfer

This app ingests supported ecommerce product URLs and returns CSV files that are importable into Shopify, Squarespace, and WooCommerce.

I use this structure:
- FastAPI API for programmatic use (`POST /api/v1/import`)
- FastAPI CSV export endpoints:
  - `POST /api/v1/export/shopify.csv`
  - `POST /api/v1/export/squarespace.csv`
  - `POST /api/v1/export/woocommerce.csv`
- Simple web UI for one-step CSV export (`/`)
- Shared importer services for Shopify, Amazon, and AliExpress

## Supported sources

- Shopify product URLs
- Amazon product URLs (requires `RAPIDAPI_KEY`)
- AliExpress item URLs (requires `RAPIDAPI_KEY`)

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
  -d '{"product_url":"https://example.myshopify.com/products/item","publish":false}' \
  -o product.csv
```

Export Squarespace CSV:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/export/squarespace.csv" \
  -H "Content-Type: application/json" \
  -d '{"product_url":"https://example.myshopify.com/products/item","publish":false,"product_page":"shop","squarespace_product_url":"lemons"}' \
  -o product.csv
```

Export WooCommerce CSV:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/export/woocommerce.csv" \
  -H "Content-Type: application/json" \
  -d '{"product_url":"https://example.myshopify.com/products/item","publish":false}' \
  -o product.csv
```

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
    importer.py
    exporters/
      shopify_csv.py
      squarespace_csv.py
      woocommerce_csv.py
  web/
    templates/index.html
    static/styles.css
tests/
```

## Tests

```bash
pytest -q
```

## Push to GitHub (private)

Create a new private repo:

```bash
git init
git add .
git commit -m "Initial import studio setup"
gh repo create <your-repo-name> --private --source . --remote origin --push
```

If remote already exists:

```bash
git remote add origin <your-private-repo-url>
git branch -M main
git push -u origin main
```
