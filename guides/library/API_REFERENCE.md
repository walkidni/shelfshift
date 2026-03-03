# Shelfshift API Reference

## Core API Reference (`shelfshift.core`)

### Input and limits

- For `detect_csv`, `import_csv`, and `convert_csv`: passing a `str` means **file path**, not raw CSV text.
- To pass raw CSV content directly, pass `bytes` (for example, `csv_text.encode("utf-8")`).
- CSV imports reject empty files.

> **Important**
> If you pass a `str` to `detect_csv`, `import_csv`, or `convert_csv`, it is treated as a file path.
> To pass raw CSV text, encode it to `bytes`.

### Result types

```python
@dataclass(frozen=True)
class DetectResult:
    kind: str
    platform: str | None
    is_product: bool
    product_id: str | None = None
    slug: str | None = None


@dataclass
class ImportResult:
    products: list[Product]
    errors: list[dict[str, str]]


@dataclass(frozen=True)
class ExportResult:
    csv_bytes: bytes
    filename: str
```

### `detect_url`

```python
def detect_url(url: str) -> DetectResult
```

Behavior

- Detects URL platform and whether the URL represents a product page.

Parameters

- `url`: product or non-product URL string.

Returns

- `DetectResult` with:
  - `kind: "url"`
  - `platform: str | None`
  - `is_product: bool`
  - `product_id: str | None`
  - `slug: str | None`

Raises

- None documented.

Example:

```python
from shelfshift.core import detect_url

result = detect_url("https://demo.myshopify.com/products/red-rain-coat")
print(result.platform)    # shopify
print(result.is_product)  # True
print(result.slug)        # red-rain-coat
```

### `detect_csv`

```python
def detect_csv(csv_input: bytes | str | pathlib.Path) -> DetectResult
```

Behavior

- When `csv_input` is `str`, it is treated as a file path.

Parameters

- CSV bytes
- path string
- `Path`

Returns

- `kind: "csv"`
- `platform: str` (detected source platform)
- `is_product: False`

Raises

- `ValueError` for unreadable, empty, or unsupported CSV input.

Example:

```python
from shelfshift.core import detect_csv

result = detect_csv("./source.csv")
print(result.platform)  # e.g. shopify
```

### `import_url`

```python
def import_url(
    urls: str | list[str],
    *,
    strict: bool = False,
) -> ImportResult
```

Behavior

- Single URL input returns one product in `result.products`.
- List input supports partial success; failed URLs appear in `result.errors`.
- `strict=True` raises `ValueError` if any URL in a batch fails.

Parameters

- `urls`: one URL (`str`) or many URLs (`list[str]`).
- `strict`: fail whole batch if any URL fails.

Returns

- `products: list[Product]`
- `errors: list[dict[str, str]]` (shape: `{"url": ..., "detail": ...}`)

Raises

- `ValueError` when `strict=True` and one or more URLs fail to import.

Example:

```python
from shelfshift.core import import_url

single = import_url("https://demo.myshopify.com/products/red-rain-coat")
product = single.products[0]

batch = import_url([
    "https://demo.myshopify.com/products/red-rain-coat",
    "https://www.amazon.com/dp/B0C1234567",  # detectable but unsupported for import
])
print(len(batch.products))
print(batch.errors)
```

Strict-mode failure example:

```python
from shelfshift.core import import_url

try:
    import_url(
        [
            "https://demo.myshopify.com/products/red-rain-coat",
            "https://www.amazon.com/dp/B0C1234567",
        ],
        strict=True,
    )
except ValueError as exc:
    print(str(exc))
    # Strict mode failed with 1 URL import error(s).
```

### `import_csv`

```python
def import_csv(
    csv_input: bytes | str | pathlib.Path,
    *,
    platform: str | None = None,
    strict: bool = False,
    source_weight_unit: str | None = None,
) -> ImportResult
```

Behavior

- If `platform` is omitted, Shelfshift auto-detects the source platform from CSV headers.
- For `bigcommerce`, `wix`, and `squarespace` sources, `source_weight_unit` is required.
- `source_weight_unit` must be one of: `g`, `kg`, `lb`, `oz`.
- `strict=True` raises if no products are imported.
- CSV must be non-empty.
- When `csv_input` is a `str`, it is treated as a file path.

Parameters

- `csv_input`: CSV bytes, file path string, or `Path`.
- `platform`: optional source platform override.
- `strict`: raises when import returns zero products.
- `source_weight_unit`: required for some sources.

Returns

- `ImportResult` with `products` and `errors` (`errors` is empty for CSV import paths).

Raises

- `ValueError` when `strict=True` and zero products are imported.

Example:

```python
from shelfshift.core import import_csv

result = import_csv("./source.csv")
print(len(result.products))

result2 = import_csv(
    "./source_bigcommerce.csv",
    platform="bigcommerce",
    source_weight_unit="kg",
)
```

Strict-mode failure example:

```python
from shelfshift.core import import_csv

try:
    import_csv("./empty.csv", strict=True)
except ValueError as exc:
    print(exc)
```

### `import_json`

```python
def import_json(
    payload: dict | list[dict] | str | bytes | pathlib.Path,
    *,
    from_file: bool = False,
) -> ImportResult
```

Use this when your source is already canonical JSON-like payload.

Behavior

- Accepts object payload (single product) or array payload (multiple products).
- Returns canonical typed `Product` objects in `ImportResult.products`.
- If passing a string path, set `from_file=True`.
- If passing a `Path`, file loading works directly.

Parameters

- `payload`: canonical product object, list of objects, JSON text (`str`/`bytes`), or path.
- `from_file`: when `True`, treat `str`/`Path` as file input (path). When `False`, `str`/`bytes` are treated as JSON payload text.

Returns

- `ImportResult`

Raises

- `ValueError` for invalid canonical payloads or unsupported payload shapes.

Example:

```python
from pathlib import Path
from shelfshift.core import import_json

single = import_json({"source": {"platform": "shopify"}, "title": "Demo"})

many = import_json([
    {"source": {"platform": "shopify"}, "title": "One"},
    {"source": {"platform": "shopify"}, "title": "Two"},
])

from_file = import_json("./canonical_products.json", from_file=True)
from_path_obj = import_json(Path("./canonical_products.json"))
```

### `export_csv`

```python
def export_csv(
    products: Product | list[Product],
    *,
    target: str,
    options: dict[str, Any] | None = None,
) -> ExportResult
```

Behavior

- `shopify`: `g | kg | lb | oz`
- `bigcommerce`: `g | kg | lb | oz`
- `wix`: `kg | lb`
- `squarespace`: `kg | lb`
- `woocommerce`: `kg`

Parameters

- `products`: one canonical `Product` or list of `Product`.
- `target`: target platform.
- `options`: export options dictionary.

Supported `target` values:

- `shopify`, `bigcommerce`, `wix`, `squarespace`, `woocommerce`

`options` keys:

- `publish: bool` (default `False`)
- `weight_unit: str`
- `bigcommerce_csv_format: "modern" | "legacy"` (default `modern`)
- `squarespace_product_page: str`
- `squarespace_product_url: str`

Returns

- `csv_bytes: bytes`
- `filename: str`

Raises

- `ValueError` for unsupported `target` platform or invalid export options.

Example:

```python
from pathlib import Path
from shelfshift.core import import_url, export_csv

imported = import_url("https://demo.myshopify.com/products/red-rain-coat")
exported = export_csv(
    imported.products,
    target="woocommerce",
    options={"publish": False, "weight_unit": "kg"},
)
Path("woocommerce.csv").write_bytes(exported.csv_bytes)
print(exported.filename)
```

### `convert_csv`

```python
def convert_csv(
    csv_input: bytes | str | pathlib.Path,
    *,
    target: str,
    source: str | None = None,
    strict: bool = False,
    source_weight_unit: str | None = None,
    export_options: dict[str, Any] | None = None,
) -> tuple[bytes, dict[str, Any]]
```

Behavior

1. import source CSV into canonical products
2. export canonical products to target CSV

Parameters

- `csv_input`: CSV bytes, file path string, or `Path`.
- `target`: target platform.
- `source`: optional source platform override.
- `strict`: propagated to `import_csv`.
- `source_weight_unit`: propagated to `import_csv`.
- `export_options`: propagated to `export_csv`.

Returns

- `csv_bytes: bytes`
- `report: dict` with keys: `source_platform`, `target_platform`, `product_count`, `errors`, `filename`

Raises

- Propagates `ValueError` from `import_csv(...)` (for example with `strict=True` and zero imported products).

Example:

```python
from pathlib import Path
from shelfshift.core import convert_csv

csv_bytes, report = convert_csv(
    "./source.csv",
    source="squarespace",
    source_weight_unit="kg",
    target="shopify",
    export_options={"weight_unit": "g"},
)
Path("shopify.csv").write_bytes(csv_bytes)
print(report)
```

### `validate`

```python
def validate(products: Product | list[Product]) -> list[ValidationReport]
```

Behavior

- Runs baseline validation checks on each product.

Parameters

- `products`: one `Product` or list of `Product`.

`ValidationReport`:

- `valid: bool`
- `issues: list[ValidationIssue]`

`ValidationIssue`:

- `code: str`
- `message: str`
- `severity: str` (default `"error"`)
- `field: str | None`

Current baseline checks include:

- missing title
- missing variants

Returns

- one `ValidationReport` per product.

Raises

- None documented.

Example:

```python
from shelfshift.core import import_csv, validate

products = import_csv("./source.csv").products
reports = validate(products)
for i, report in enumerate(reports, start=1):
    print(i, report.valid)
    for issue in report.issues:
        print(issue.code, issue.field, issue.message)
```

### `json_to_product` and `json_to_products`

These are also available directly from `shelfshift.core.canonical.io`.

```python
def json_to_product(
    payload: dict[str, Any] | str | bytes | pathlib.Path,
    *,
    from_file: bool = False,
) -> Product


def json_to_products(
    payload: list[dict[str, Any]] | str | bytes | pathlib.Path,
    *,
    from_file: bool = False,
) -> list[Product]
```

Use these if you want canonical type hydration without the `ImportResult` wrapper.

Behavior

- Hydrates canonical typed `Product` objects directly from canonical JSON payloads.

Parameters

- `payload`: canonical object/list payload, JSON text, or path (depending on function and `from_file`).
- `from_file`: when `True`, treat path-like input as file input.

Returns

- `json_to_product(...) -> Product`
- `json_to_products(...) -> list[Product]`

Raises

- `ValueError` for invalid canonical payloads or unsupported payload shapes.

Example:

```python
from shelfshift.core import json_to_product, json_to_products

single = json_to_product({"source": {"platform": "shopify"}, "title": "Demo"})
many = json_to_products([
    {"source": {"platform": "shopify"}, "title": "One"},
    {"source": {"platform": "shopify"}, "title": "Two"},
])
```

---

Previous: [Core Concepts](./CORE_CONCEPTS.md) | Next: [Canonical Model](./CANONICAL_MODEL.md)
