WOOCOMMERCE_WEIGHT_HEADER_PLACEHOLDER = "__WEIGHT_HEADER__"
WOOCOMMERCE_WEIGHT_HEADER_BY_UNIT: dict[str, str] = {
    "lb": "Weight (lbs)",
    "kg": "Weight (kg)",
    "g": "Weight (g)",
    "oz": "Weight (oz)",
}
WOOCOMMERCE_WEIGHT_UNIT_BY_HEADER: dict[str, str] = {
    header: unit for unit, header in WOOCOMMERCE_WEIGHT_HEADER_BY_UNIT.items()
}

WOOCOMMERCE_COLUMNS: list[str] = [
    "ID",
    "Type",
    "SKU",
    "Name",
    "Published",
    "Is featured?",
    "Visibility in catalog",
    "Short description",
    "Description",
    "Date sale price starts",
    "Date sale price ends",
    "Tax status",
    "Tax class",
    "In stock?",
    "Stock",
    "Backorders allowed?",
    "Sold individually?",
    WOOCOMMERCE_WEIGHT_HEADER_PLACEHOLDER,
    "Length (in)",
    "Width (in)",
    "Height (in)",
    "Allow customer reviews?",
    "Purchase note",
    "Sale price",
    "Regular price",
    "Categories",
    "Tags",
    "Shipping class",
    "Images",
    "Download limit",
    "Download expiry days",
    "Parent",
    "Grouped products",
    "Upsells",
    "Cross-sells",
    "External URL",
    "Button text",
    "Position",
    "Attribute 1 name",
    "Attribute 1 value(s)",
    "Attribute 1 visible",
    "Attribute 1 global",
    "Attribute 2 name",
    "Attribute 2 value(s)",
    "Attribute 2 visible",
    "Attribute 2 global",
    "Meta: _wpcom_is_markdown",
    "Download 1 name",
    "Download 1 URL",
    "Download 2 name",
    "Download 2 URL",
]

WOOCOMMERCE_REQUIRED_HEADERS = ("Type", "SKU", "Name", "Regular price")
WOOCOMMERCE_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "id": ("ID",),
    "sku": ("SKU",),
    "name": ("Name",),
    "description": ("Description",),
    "short_description": ("Short description",),
    "tags": ("Tags",),
    "categories": ("Categories",),
    "regular_price": ("Regular price",),
    "stock": ("Stock",),
    "in_stock": ("In stock?",),
    "tax_status": ("Tax status",),
    "published": ("Published",),
    "images": ("Images",),
}
WOOCOMMERCE_ATTRIBUTE_NAME_TEMPLATE = "Attribute {i} name"
WOOCOMMERCE_ATTRIBUTE_VALUES_TEMPLATE = "Attribute {i} value(s)"


def woocommerce_columns_for_weight_unit(weight_unit: str | None = None) -> list[str]:
    resolved_weight_unit = str(weight_unit or "").strip().lower() or "kg"
    weight_header = WOOCOMMERCE_WEIGHT_HEADER_BY_UNIT[resolved_weight_unit]
    return [
        weight_header if column == WOOCOMMERCE_WEIGHT_HEADER_PLACEHOLDER else column
        for column in WOOCOMMERCE_COLUMNS
    ]
