# Shelfshift CLI Advanced Usage

## Minimal Canonical Product Shape

```json
{
  "source": {"platform": "shopify", "id": "123", "slug": "demo-item", "url": "https://example.com/products/demo-item"},
  "title": "Demo Item",
  "description": "Demo description",
  "tags": ["tag-a", "tag-b"],
  "options": [{"name": "Size", "values": ["S", "M"]}],
  "variants": [
    {
      "sku": "DEMO-S",
      "option_values": [{"name": "Size", "value": "S"}],
      "price": {"current": {"amount": "19.99", "currency": "USD"}},
      "inventory": {"track_quantity": true, "quantity": 10, "available": true, "allow_backorder": false},
      "weight": {"value": "250", "unit": "g"}
    }
  ],
  "price": {"current": {"amount": "19.99", "currency": "USD"}},
  "weight": {"value": "250", "unit": "g"},
  "media": [{"url": "https://cdn.example.com/image.jpg", "type": "image"}],
  "identifiers": {"values": {"barcode": "0123456789"}}
}
```

## Edit Canonical JSON Before Export

```bash
shelfshift import-url "https://example.myshopify.com/products/demo-item" > import_result.json
python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("import_result.json").read_text(encoding="utf-8"))
products = data["products"]

products[0]["title"] = "Edited via CLI workflow"
products[0]["tags"] = ["featured", "spring"]

Path("products_edited.json").write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
PY
shelfshift export-csv ./products_edited.json --to shopify --out ./shopify.csv
```

## End-to-End Example (Import URL -> Export CSV)

`import-url` returns an envelope (`{"products": [...], "errors": [...]}`), so extract the `products` array before using `export-csv`:

```bash
shelfshift import-url "https://example.myshopify.com/products/demo-item" > import_result.json
python - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("import_result.json").read_text(encoding="utf-8"))
Path("products_only.json").write_text(
    json.dumps(payload["products"], ensure_ascii=False, indent=2),
    encoding="utf-8",
)
PY
shelfshift export-csv ./products_only.json --to shopify --out ./shopify.csv
```

---

Previous: [CLI Command Reference](./COMMAND_REFERENCE.md) | Next: [CLI Guide Index](./INDEX.md)
