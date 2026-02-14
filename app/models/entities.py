from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

Currency = str
WeightUnit = Literal["g", "kg", "lb", "oz"]
MediaType = Literal["image", "video"]


@dataclass
class Money:
    amount: Decimal | None = None
    currency: Currency | None = None


@dataclass
class Price:
    current: Money = field(default_factory=Money)
    compare_at: Money | None = None
    cost: Money | None = None
    min_price: Money | None = None
    max_price: Money | None = None


@dataclass
class Weight:
    value: Decimal | None = None
    unit: WeightUnit = "g"


@dataclass
class Media:
    url: str
    type: MediaType = "image"
    alt: str | None = None
    position: int | None = None
    is_primary: bool | None = None
    variant_skus: list[str] = field(default_factory=list)


@dataclass
class OptionDef:
    name: str
    values: list[str] = field(default_factory=list)


@dataclass
class OptionValue:
    name: str
    value: str


@dataclass
class Inventory:
    track_quantity: bool | None = None
    quantity: int | None = None
    available: bool | None = None
    allow_backorder: bool | None = None


@dataclass
class Seo:
    title: str | None = None
    description: str | None = None


@dataclass
class SourceRef:
    platform: str
    id: str | None = None
    slug: str | None = None
    url: str | None = None


@dataclass
class CategorySet:
    paths: list[list[str]] = field(default_factory=list)
    primary: list[str] | None = None


@dataclass
class Identifiers:
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class Variant:
    id: str | None = None
    sku: str | None = None
    title: str | None = None
    option_values: list[OptionValue] = field(default_factory=list)
    price: Price | None = None
    inventory: Inventory = field(default_factory=Inventory)
    weight: Weight | None = None
    media: list[Media] = field(default_factory=list)
    identifiers: Identifiers = field(default_factory=Identifiers)
    raw: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.option_values = _normalize_option_values(self.option_values)

        if isinstance(self.price, dict):
            self.price = _price_from_payload(self.price)

        if isinstance(self.inventory, dict):
            self.inventory = _inventory_from_payload(self.inventory)
        if self.inventory is None:
            self.inventory = Inventory()

        self.weight = _weight_from_payload(self.weight)
        self.media = _normalize_media_list(self.media)

        if isinstance(self.identifiers, dict):
            self.identifiers = Identifiers(values=_clean_identifier_values(self.identifiers))

    def to_dict(self, include_raw: bool = True) -> dict[str, Any]:
        data = {
            "id": self.id,
            "sku": self.sku,
            "title": self.title,
            "option_values": [
                {"name": option.name, "value": option.value}
                for option in self.option_values
            ],
            "price": _price_to_dict(self.price),
            "inventory": {
                "track_quantity": self.inventory.track_quantity,
                "quantity": self.inventory.quantity,
                "available": self.inventory.available,
                "allow_backorder": self.inventory.allow_backorder,
            },
            "weight": _weight_to_dict(self.weight),
            "media": [_media_to_dict(item) for item in self.media],
            "identifiers": {"values": dict(self.identifiers.values)},
        }
        if include_raw:
            data["raw"] = self.raw
        return data


@dataclass
class Product:
    source: SourceRef = field(default_factory=lambda: SourceRef(platform="unknown"))
    title: str | None = None
    description: str | None = None
    seo: Seo = field(default_factory=Seo)
    brand: str | None = None
    vendor: str | None = None
    taxonomy: CategorySet = field(default_factory=CategorySet)
    tags: list[str] = field(default_factory=list)
    options: list[OptionDef] = field(default_factory=list)
    variants: list[Variant] = field(default_factory=list)
    price: Price | None = None
    weight: Weight | None = None
    requires_shipping: bool = True
    track_quantity: bool = True
    is_digital: bool = False
    media: list[Media] = field(default_factory=list)
    identifiers: Identifiers = field(default_factory=Identifiers)
    raw: dict[str, Any] | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.source, dict):
            self.source = SourceRef(
                platform=str(self.source.get("platform") or "unknown"),
                id=_clean_text(self.source.get("id")),
                slug=_clean_text(self.source.get("slug")),
                url=_normalize_url(self.source.get("url")),
            )

        if isinstance(self.seo, dict):
            self.seo = Seo(
                title=_clean_text(self.seo.get("title")),
                description=_clean_text(self.seo.get("description")),
            )

        if self.taxonomy is None:
            self.taxonomy = CategorySet()
        if isinstance(self.taxonomy, dict):
            raw_paths = self.taxonomy.get("paths")
            raw_primary = self.taxonomy.get("primary")
            self.taxonomy = CategorySet(
                paths=_normalize_paths(raw_paths),
                primary=_normalize_path(raw_primary),
            )

        if self.taxonomy.primary is None and self.taxonomy.paths:
            self.taxonomy.primary = list(self.taxonomy.paths[0])

        self.tags = _ordered_unique_strings(self.tags)
        self.options = _normalize_option_defs(self.options)

        if isinstance(self.price, dict):
            self.price = _price_from_payload(self.price)

        self.weight = _weight_from_payload(self.weight)
        self.media = _normalize_media_list(self.media)

        if isinstance(self.identifiers, dict):
            self.identifiers = Identifiers(values=_clean_identifier_values(self.identifiers))

        cleaned_source_platform = _clean_text(self.source.platform)
        self.source.platform = cleaned_source_platform or "unknown"
        self.source.id = _clean_text(self.source.id)
        self.source.slug = _clean_text(self.source.slug)
        self.source.url = _normalize_url(self.source.url)

    def to_dict(self, include_raw: bool = True) -> dict[str, Any]:
        data = {
            "source": {
                "platform": self.source.platform,
                "id": self.source.id,
                "slug": self.source.slug,
                "url": self.source.url,
            },
            "title": self.title,
            "description": self.description,
            "seo": {
                "title": self.seo.title,
                "description": self.seo.description,
            },
            "brand": self.brand,
            "vendor": self.vendor,
            "taxonomy": {
                "paths": [list(path) for path in self.taxonomy.paths],
                "primary": list(self.taxonomy.primary) if self.taxonomy.primary else None,
            },
            "tags": list(self.tags),
            "options": [
                {"name": option.name, "values": list(option.values)}
                for option in self.options
            ],
            "variants": [variant.to_dict(include_raw=include_raw) for variant in self.variants],
            "price": _price_to_dict(self.price),
            "weight": _weight_to_dict(self.weight),
            "requires_shipping": self.requires_shipping,
            "track_quantity": self.track_quantity,
            "is_digital": self.is_digital,
            "media": [_media_to_dict(item) for item in self.media],
            "identifiers": {"values": dict(self.identifiers.values)},
            "provenance": dict(self.provenance),
        }
        if include_raw:
            data["raw"] = self.raw
        return data


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ordered_unique_strings(items: list[Any] | tuple[Any, ...] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items or []:
        cleaned = _clean_text(item)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value if value.is_finite() else None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return parsed if parsed.is_finite() else None


def _normalize_currency(value: Any) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    return cleaned.upper()


def _normalize_weight_unit(value: Any) -> WeightUnit:
    normalized = _clean_text(value)
    if normalized is None:
        return "g"
    lowered = normalized.lower()
    if lowered in {"g", "kg", "lb", "oz"}:
        return lowered  # type: ignore[return-value]
    return "g"


def _normalize_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped.startswith("//"):
        return f"https:{stripped}"
    return stripped


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None or not value.is_finite():
        return None
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _clean_identifier_values(values: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in (values or {}).items():
        key_str = _clean_text(key)
        value_str = _clean_text(value)
        if not key_str or not value_str:
            continue
        out[key_str] = value_str
    return out


def _normalize_option_values(
    values: list[OptionValue] | list[dict[str, str]] | dict[str, str] | None,
) -> list[OptionValue]:
    if isinstance(values, dict):
        values = [
            {"name": str(name), "value": str(value)}
            for name, value in values.items()
        ]

    out: list[OptionValue] = []
    for item in values or []:
        if isinstance(item, OptionValue):
            name = _clean_text(item.name)
            value = _clean_text(item.value)
        elif isinstance(item, dict):
            name = _clean_text(item.get("name"))
            value = _clean_text(item.get("value"))
        else:
            continue
        if not name or not value:
            continue
        out.append(OptionValue(name=name, value=value))
    return out


def _normalize_option_defs(
    values: list[OptionDef] | list[dict[str, Any]] | dict[str, list[str]] | None,
) -> list[OptionDef]:
    if isinstance(values, dict):
        values = [
            {"name": str(name), "values": raw_values}
            for name, raw_values in values.items()
        ]

    out: list[OptionDef] = []
    for item in values or []:
        if isinstance(item, OptionDef):
            name = _clean_text(item.name)
            option_values = _ordered_unique_strings(item.values)
        elif isinstance(item, dict):
            name = _clean_text(item.get("name"))
            raw_values = item.get("values")
            if isinstance(raw_values, (list, tuple)):
                option_values = _ordered_unique_strings(list(raw_values))
            elif raw_values is None:
                option_values = []
            else:
                option_values = _ordered_unique_strings([raw_values])
        else:
            continue
        if not name:
            continue
        out.append(OptionDef(name=name, values=option_values))
    return out


def _normalize_media_list(values: list[Media] | list[dict[str, Any]] | None) -> list[Media]:
    out: list[Media] = []
    for item in values or []:
        if isinstance(item, Media):
            normalized_url = _normalize_url(item.url)
            if not normalized_url:
                continue
            out.append(
                Media(
                    url=normalized_url,
                    type=item.type,
                    alt=item.alt,
                    position=item.position,
                    is_primary=item.is_primary,
                    variant_skus=[str(sku) for sku in item.variant_skus if str(sku).strip()],
                )
            )
            continue

        if isinstance(item, dict):
            normalized_url = _normalize_url(item.get("url"))
            if not normalized_url:
                continue
            media_type = str(item.get("type") or "image").strip().lower()
            if media_type not in {"image", "video"}:
                media_type = "image"
            out.append(
                Media(
                    url=normalized_url,
                    type=media_type,
                    alt=(str(item.get("alt")).strip() if item.get("alt") is not None else None) or None,
                    position=item.get("position") if isinstance(item.get("position"), int) else None,
                    is_primary=item.get("is_primary") if isinstance(item.get("is_primary"), bool) else None,
                    variant_skus=[
                        str(sku)
                        for sku in item.get("variant_skus", [])
                        if isinstance(sku, str) and sku.strip()
                    ],
                )
            )

    return _dedupe_media(out)


def _dedupe_media(values: list[Media]) -> list[Media]:
    out: list[Media] = []
    seen: set[tuple[str, str]] = set()
    for item in values:
        key = (item.type, item.url)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _normalize_path(path: Any) -> list[str] | None:
    if not isinstance(path, (list, tuple)):
        return None
    normalized = _ordered_unique_strings(list(path))
    return normalized or None


def _normalize_paths(raw_paths: Any) -> list[list[str]]:
    if not isinstance(raw_paths, list):
        return []

    normalized: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for raw_path in raw_paths:
        if not isinstance(raw_path, (list, tuple)):
            continue
        path = _ordered_unique_strings(list(raw_path))
        if not path:
            continue
        key = tuple(path)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(path)
    return normalized


def _money_from_payload(payload: Any) -> Money | None:
    if isinstance(payload, Money):
        return Money(
            amount=_parse_decimal(payload.amount),
            currency=_normalize_currency(payload.currency),
        )
    if not isinstance(payload, dict):
        return None

    amount = _parse_decimal(payload.get("amount"))
    currency = _normalize_currency(payload.get("currency"))
    if amount is None and currency is None:
        return None
    return Money(amount=amount, currency=currency)


def _price_from_payload(payload: Any) -> Price | None:
    if isinstance(payload, Price):
        return Price(
            current=_money_from_payload(payload.current) or Money(),
            compare_at=_money_from_payload(payload.compare_at),
            cost=_money_from_payload(payload.cost),
            min_price=_money_from_payload(payload.min_price),
            max_price=_money_from_payload(payload.max_price),
        )

    if not isinstance(payload, dict):
        return None

    if "current" in payload:
        current = _money_from_payload(payload.get("current")) or Money()
        compare_at = _money_from_payload(payload.get("compare_at"))
        cost = _money_from_payload(payload.get("cost"))
        min_price = _money_from_payload(payload.get("min_price"))
        max_price = _money_from_payload(payload.get("max_price"))
        if (
            current.amount is None
            and current.currency is None
            and compare_at is None
            and cost is None
            and min_price is None
            and max_price is None
        ):
            return None
        return Price(
            current=current,
            compare_at=compare_at,
            cost=cost,
            min_price=min_price,
            max_price=max_price,
        )

    amount = _parse_decimal(payload.get("amount"))
    currency = _normalize_currency(payload.get("currency"))
    if amount is None and currency is None:
        return None
    return Price(current=Money(amount=amount, currency=currency))


def _weight_from_payload(payload: Any) -> Weight | None:
    if isinstance(payload, Weight):
        value = _parse_decimal(payload.value)
        if value is None:
            return None
        return Weight(value=value, unit=_normalize_weight_unit(payload.unit))

    if isinstance(payload, dict):
        value = _parse_decimal(payload.get("value"))
        if value is None:
            return None
        return Weight(value=value, unit=_normalize_weight_unit(payload.get("unit")))

    value = _parse_decimal(payload)
    if value is None:
        return None
    return Weight(value=value, unit="g")


def _inventory_from_payload(payload: Any) -> Inventory:
    if isinstance(payload, Inventory):
        return Inventory(
            track_quantity=payload.track_quantity,
            quantity=payload.quantity,
            available=payload.available,
            allow_backorder=payload.allow_backorder,
        )
    if not isinstance(payload, dict):
        return Inventory()
    quantity = payload.get("quantity")
    if quantity is not None:
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = None
    return Inventory(
        track_quantity=payload.get("track_quantity") if isinstance(payload.get("track_quantity"), bool) else None,
        quantity=quantity,
        available=payload.get("available") if isinstance(payload.get("available"), bool) else None,
        allow_backorder=payload.get("allow_backorder") if isinstance(payload.get("allow_backorder"), bool) else None,
    )


def _money_to_dict(money: Money | None) -> dict[str, str | None] | None:
    if money is None:
        return None
    amount = _format_decimal(money.amount)
    currency = _normalize_currency(money.currency)
    if amount is None and currency is None:
        return None
    return {
        "amount": amount,
        "currency": currency,
    }


def _price_to_dict(price: Price | None) -> dict[str, Any] | None:
    if price is None:
        return None
    current = _money_to_dict(price.current)
    compare_at = _money_to_dict(price.compare_at)
    cost = _money_to_dict(price.cost)
    min_price = _money_to_dict(price.min_price)
    max_price = _money_to_dict(price.max_price)
    if current is None and compare_at is None and cost is None and min_price is None and max_price is None:
        return None
    return {
        "current": current,
        "compare_at": compare_at,
        "cost": cost,
        "min_price": min_price,
        "max_price": max_price,
    }


def _weight_to_dict(weight: Weight | None) -> dict[str, str] | None:
    if weight is None:
        return None
    value = _format_decimal(_parse_decimal(weight.value))
    if value is None:
        return None
    return {
        "value": value,
        "unit": _normalize_weight_unit(weight.unit),
    }


def _media_to_dict(media: Media) -> dict[str, Any]:
    return {
        "url": media.url,
        "type": media.type,
        "alt": media.alt,
        "position": media.position,
        "is_primary": media.is_primary,
        "variant_skus": list(media.variant_skus),
    }


__all__ = [
    "CategorySet",
    "Currency",
    "Identifiers",
    "Inventory",
    "Media",
    "MediaType",
    "Money",
    "OptionDef",
    "OptionValue",
    "Price",
    "Product",
    "Seo",
    "SourceRef",
    "Variant",
    "Weight",
    "WeightUnit",
]
