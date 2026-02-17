from typing import Literal, cast

WeightUnit = Literal["g", "kg", "lb", "oz"]

WEIGHT_UNIT_ALLOWLIST_BY_TARGET: dict[str, tuple[WeightUnit, ...]] = {
    "shopify": ("g", "kg", "lb", "oz"),
    "bigcommerce": ("g", "kg", "lb", "oz"),
    "wix": ("kg", "lb"),
    "squarespace": ("kg", "lb"),
    "woocommerce": ("kg",),
}

DEFAULT_WEIGHT_UNIT_BY_TARGET: dict[str, WeightUnit] = {
    "shopify": "g",
    "bigcommerce": "kg",
    "wix": "kg",
    "squarespace": "kg",
    "woocommerce": "kg",
}


def resolve_weight_unit(target_platform: str, requested_weight_unit: str | None) -> WeightUnit:
    target = (target_platform or "").strip().lower()
    allowlist = WEIGHT_UNIT_ALLOWLIST_BY_TARGET.get(target)
    if allowlist is None:
        raise ValueError("target_platform must be one of: shopify, bigcommerce, wix, squarespace, woocommerce")

    requested = (requested_weight_unit or "").strip().lower()
    if not requested:
        return DEFAULT_WEIGHT_UNIT_BY_TARGET[target]

    if requested not in allowlist:
        supported = ", ".join(allowlist)
        raise ValueError(f"weight_unit must be one of: {supported} for target_platform={target}")

    return cast(WeightUnit, requested)
