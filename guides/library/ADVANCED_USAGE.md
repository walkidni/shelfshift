# Shelfshift Advanced Usage

## Common End-to-End Workflows

### A) URL import -> edit canonical typed product -> export CSV

```python
from pathlib import Path
from shelfshift.core import import_url, export_csv

imported = import_url("https://demo.myshopify.com/products/red-rain-coat")
product = imported.products[0]
product.title = "Edited Title"

exported = export_csv(product, target="bigcommerce", options={"bigcommerce_csv_format": "modern"})
Path("bigcommerce.csv").write_bytes(exported.csv_bytes)
```

### B) CSV import -> validate -> export

```python
from pathlib import Path
from shelfshift.core import import_csv, validate, export_csv

imported = import_csv("./source_wix.csv", platform="wix", source_weight_unit="kg")
reports = validate(imported.products)

if all(r.valid for r in reports):
    exported = export_csv(imported.products, target="shopify", options={"weight_unit": "g"})
    Path("shopify.csv").write_bytes(exported.csv_bytes)
```

### C) Canonical JSON file -> typed products -> export

```python
from pathlib import Path
from shelfshift.core import import_json, export_csv

imported = import_json("./canonical_products.json", from_file=True)
exported = export_csv(imported.products, target="woocommerce", options={"weight_unit": "kg"})
Path("woocommerce.csv").write_bytes(exported.csv_bytes)
```

---

## Error Handling Notes

Common `ValueError` cases:

- unsupported URL import source (`amazon` / `aliexpress`)
- unsupported CSV source platform
- CSV empty
- missing/invalid `source_weight_unit` for `bigcommerce`/`wix`/`squarespace`
- unsupported export target
- unsupported export `weight_unit` for target platform
- strict mode failures in URL batch import or empty CSV import result

Practical pattern:

```python
from shelfshift.core import import_url

try:
    result = import_url([
        "https://demo.myshopify.com/products/red-rain-coat",
        "https://www.amazon.com/dp/B0C1234567",
    ], strict=True)
except ValueError as exc:
    print("Import failed:", exc)
```

---

## Recommended Advanced API (Optional)

Most users should stay on `shelfshift.core`. If you need extension points or lower-level control, this is the recommended advanced subset.

### Registry extension points

Module: `shelfshift.core.registry`

```python
register_importer(key: str, handler: ImporterFn) -> None
register_exporter(key: str, handler: ExporterFn) -> None
get_importer(key: str) -> ImporterFn
get_exporter(key: str) -> ExporterFn
list_importers() -> list[str]
list_exporters() -> list[str]
```

Use this when you want to plug custom import/export handlers into Shelfshift's registry.

### Low-level detection primitives

Modules:

- `shelfshift.core.detect.csv`
```python
detect_csv_platform(csv_bytes: bytes) -> str
```

- `shelfshift.core.detect.url`
```python
detect_product_url(url: str) -> dict
```

Use these when you need raw platform-detection behavior outside the `DetectResult` wrapper.

### Single-product validation primitive

Module: `shelfshift.core.validate.rules`

```python
validate_product(product: Product) -> ValidationReport
```

Use this for custom pipelines that validate one product at a time.

### URL importer primitives

Module: `shelfshift.core.importers.url`

```python
normalize_product_url(product_url: str) -> str
import_products_from_urls(urls: list[str]) -> tuple[list[Product], list[dict[str, str]]]
```

Use these when you need explicit URL normalization or batch partial-failure tuples directly.

### Canonical helper functions

Module: `shelfshift.core.canonical.helpers`

```python
parse_decimal_money(value: Any) -> Decimal | None
normalize_currency(value: Any) -> str | None
format_decimal(value: Decimal | None) -> str
resolve_option_defs(product: Product) -> list[OptionDef]
resolve_variant_option_values(product: Product, variant: Variant) -> list[OptionValue]
resolve_taxonomy_paths(product: Product) -> list[list[str]]
resolve_current_money(product: Product, variant: Variant | None = None) -> Money | None
resolve_primary_image_url(product: Product, variant: Variant | None = None) -> str | None
resolve_all_image_urls(product: Product) -> list[str]
```

Use these when you need deterministic canonical normalization/derivation helpers in custom integrations.

### Platform row mappers (pre-CSV control)

Use these low-level mappers when you want platform-ready row dictionaries before CSV serialization.

- Shopify (`shelfshift.core.exporters.platforms.shopify`)
```python
product_to_shopify_rows(
    product: Product,
    *,
    publish: bool,
    weight_unit: str = "g",
) -> list[dict[str, str]]
```

- BigCommerce (`shelfshift.core.exporters.platforms.bigcommerce`)
```python
product_to_bigcommerce_rows(
    product: Product,
    *,
    publish: bool,
    csv_format: Literal["modern", "legacy"] = "modern",
    weight_unit: str = "kg",
) -> list[dict[str, str]]
```

- Wix (`shelfshift.core.exporters.platforms.wix`)
```python
product_to_wix_rows(
    product: Product,
    *,
    publish: bool,
    weight_unit: str = "kg",
) -> list[dict[str, str]]
```

- Squarespace (`shelfshift.core.exporters.platforms.squarespace`)
```python
product_to_squarespace_rows(
    product: Product,
    *,
    publish: bool,
    product_page: str = "",
    product_url: str = "",
    weight_unit: str = "kg",
) -> list[dict[str, str]]
```

- WooCommerce (`shelfshift.core.exporters.platforms.woocommerce`)
```python
product_to_woocommerce_rows(
    product: Product,
    *,
    publish: bool,
    weight_unit: str = "kg",
) -> list[dict[str, str]]
```

Use these when you want platform-ready CSV row dicts for custom post-processing before writing CSV text.

---

Previous: [Canonical Model](./CANONICAL_MODEL.md) | Next: [Core Library Guide Index](./INDEX.md)
