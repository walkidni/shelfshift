# Shelfshift Core Concepts

## How Shelfshift Works

Shelfshift follows a 3-step pipeline:

1. Detect source type/platform (`detect_url`, `detect_csv`).
2. Normalize data into the canonical typed `Product` model.
3. Export canonical products into target CSV format.

All import and conversion flows go through the canonical layer, so you can inspect/edit `Product` data before export.

---

## Public Library Surfaces

### 1) Main facade: `shelfshift.core`

Use this for almost all workflows.

```python
from shelfshift.core import (
    detect_url,
    detect_csv,
    import_url,
    import_csv,
    import_json,
    export_csv,
    convert_csv,
    validate,
    json_to_product,
    json_to_products,
)
```

#### Main Facade Function Index

All functions available from the `shelfshift.core` facade:

```python
def detect_url(url: str) -> DetectResult
def detect_csv(csv_input: bytes | str | pathlib.Path) -> DetectResult

def import_url(
    urls: str | list[str],
    *,
    strict: bool = False,
) -> ImportResult

def import_csv(
    csv_input: bytes | str | pathlib.Path,
    *,
    platform: str | None = None,
    strict: bool = False,
    source_weight_unit: str | None = None,
) -> ImportResult

def import_json(
    payload: dict[str, Any] | list[dict[str, Any]] | str | bytes | pathlib.Path,
    *,
    from_file: bool = False,
) -> ImportResult

def export_csv(
    products: Product | list[Product],
    *,
    target: str,
    options: dict[str, Any] | None = None,
) -> ExportResult

def convert_csv(
    csv_input: bytes | str | pathlib.Path,
    *,
    target: str,
    source: str | None = None,
    strict: bool = False,
    source_weight_unit: str | None = None,
    export_options: dict[str, Any] | None = None,
) -> tuple[bytes, dict[str, Any]]

def validate(products: Product | list[Product]) -> list[ValidationReport]

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

### 2) Canonical typed models: `shelfshift.core.canonical`

Use this when you want typed `Product` manipulation.

```python
from shelfshift.core.canonical import Product, Variant, Price, Money, Weight
```

### 3) Convenience top-level facade: `shelfshift`

Top-level `shelfshift` re-exports most high-level functions from `shelfshift.core`.

```python
from shelfshift import import_url, export_csv
```

#### Top-Level Facade Function Index (`shelfshift/__init__.py`)

```python
__version__: str

def detect_url(url: str) -> DetectResult
def detect_csv(csv_input: bytes | str | pathlib.Path) -> DetectResult

def import_url(
    urls: str | list[str],
    *,
    strict: bool = False,
) -> ImportResult

def import_csv(
    csv_input: bytes | str | pathlib.Path,
    *,
    platform: str | None = None,
    strict: bool = False,
    source_weight_unit: str | None = None,
) -> ImportResult

def import_json(
    payload: dict[str, Any] | list[dict[str, Any]] | str | bytes | pathlib.Path,
    *,
    from_file: bool = False,
) -> ImportResult

def export_csv(
    products: Product | list[Product],
    *,
    target: str,
    options: dict[str, Any] | None = None,
) -> ExportResult

def convert_csv(
    csv_input: bytes | str | pathlib.Path,
    *,
    target: str,
    source: str | None = None,
    strict: bool = False,
    source_weight_unit: str | None = None,
    export_options: dict[str, Any] | None = None,
) -> tuple[bytes, dict[str, Any]]

def validate(products: Product | list[Product]) -> list[ValidationReport]
```

Note: `json_to_product` / `json_to_products` are only on `shelfshift.core`, not top-level `shelfshift`.

### When to Use What

| Situation | Use |
| --- | --- |
| Convert CSV to CSV | `convert_csv` |
| Inspect canonical product | `import_*` |
| Custom pipeline | canonical models + `export_csv` |
| Extend platforms | registry |

---

## Supported Platforms

### Detect-only platforms

- `amazon`
- `aliexpress`

These platforms are intentionally detection-only in the current core API. `import_url(...)` supports Shopify, WooCommerce, and Squarespace only.

### URL detection platforms

- `shopify`
- `woocommerce`
- `squarespace`
- `amazon`
- `aliexpress`

### URL import platforms

- `shopify`
- `woocommerce`
- `squarespace`

Important: Amazon and AliExpress are detectable by `detect_url(...)`, but **not** supported by `import_url(...)`.

### CSV detection/import source platforms

- `shopify`
- `bigcommerce`
- `wix`
- `squarespace`
- `woocommerce`

### CSV export target platforms

- `shopify`
- `bigcommerce`
- `wix`
- `squarespace`
- `woocommerce`

### Weight unit matrix

| Platform | Import requires `source_weight_unit`? | Export `weight_unit` options | Export default |
| --- | --- | --- | --- |
| `shopify` | No | `g`, `kg`, `lb`, `oz` | `g` |
| `bigcommerce` | Yes | `g`, `kg`, `lb`, `oz` | `kg` |
| `wix` | Yes | `kg`, `lb` | `kg` |
| `squarespace` | Yes | `kg`, `lb` | `kg` |
| `woocommerce` | No | `kg` | `kg` |

---

Previous: [Getting Started](./GETTING_STARTED.md) | Next: [API Reference](./API_REFERENCE.md)
