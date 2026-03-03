# Shelfshift Canonical Model

## Canonical Typed Product Model

The canonical model is defined in `shelfshift.core.canonical`.

### Main type: `Product`

```python
@dataclass
class Product:
    source: SourceRef
    title: str | None
    description: str | None
    seo: Seo
    brand: str | None
    vendor: str | None
    taxonomy: CategorySet
    tags: list[str]
    options: list[OptionDef]
    variants: list[Variant]
    price: Price | None
    weight: Weight | None
    requires_shipping: bool
    track_quantity: bool
    is_digital: bool
    media: list[Media]
    identifiers: Identifiers
    provenance: dict[str, Any]
```

### Nested canonical types

```python
@dataclass
class SourceRef:
    platform: str
    id: str | None
    slug: str | None
    url: str | None

@dataclass
class Variant:
    id: str | None
    sku: str | None
    title: str | None
    option_values: list[OptionValue]
    price: Price | None
    inventory: Inventory
    weight: Weight | None
    media: list[Media]
    identifiers: Identifiers

@dataclass
class Price:
    current: Money
    compare_at: Money | None
    cost: Money | None
    min_price: Money | None
    max_price: Money | None

@dataclass
class Money:
    amount: Decimal | None
    currency: str | None

@dataclass
class Weight:
    value: Decimal | None
    unit: Literal["g", "kg", "lb", "oz"]

@dataclass
class Media:
    url: str
    type: Literal["image", "video"]
    alt: str | None
    position: int | None
    is_primary: bool | None
    variant_skus: list[str]

@dataclass
class OptionDef:
    name: str
    values: list[str]

@dataclass
class OptionValue:
    name: str
    value: str

@dataclass
class Inventory:
    track_quantity: bool | None
    quantity: int | None
    available: bool | None
    allow_backorder: bool | None

@dataclass
class Seo:
    title: str | None
    description: str | None

@dataclass
class CategorySet:
    paths: list[list[str]]
    primary: list[str] | None

@dataclass
class Identifiers:
    values: dict[str, str]
```

### Important behavior

- `Product(**payload_dict)` and `Variant(**payload_dict)` normalize many nested dict inputs into typed canonical dataclasses.
- Canonical fields produced by `to_dict()` are JSON-friendly dict/list primitives.
- Decimal values in canonical money/weight fields are serialized as strings in `to_dict()` output (for stable JSON/CSV handling).

Example typed manipulation:

```python
from decimal import Decimal
from shelfshift.core import import_url, export_csv
from shelfshift.core.canonical import Money, Price

result = import_url("https://demo.myshopify.com/products/red-rain-coat")
product = result.products[0]

product.title = "Red Rain Coat v2"
product.tags = [*product.tags, "spring-2026"]

if product.price is None:
    product.price = Price(current=Money())
product.price.current.amount = Decimal("49.99")
product.price.current.currency = "USD"

csv_result = export_csv(product, target="shopify", options={"weight_unit": "g"})
```

---

Previous: [API Reference](./API_REFERENCE.md) | Next: [Advanced Usage](./ADVANCED_USAGE.md)
