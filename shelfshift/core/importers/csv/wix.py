from ...canonical import Identifiers, Inventory, Product, Seo, SourceRef, Variant
from ...exporters.platforms.wix import WIX_COLUMNS

from .common import (
    add_csv_provenance,
    apply_extra_product_fields,
    apply_extra_variant_fields,
    csv_rows,
    media_from_urls,
    option_defs_from_option_maps,
    parse_float,
    parse_int,
    price_from_amount,
    require_headers,
    split_tokens,
    weight_object,
    weight_to_grams,
)


_REQUIRED_HEADERS = ("handle", "fieldType", "name", "price", "sku")


def _variant_inventory_from_wix(value: str) -> Inventory:
    quantity = parse_int(value)
    if quantity is not None:
        return Inventory(track_quantity=True, quantity=quantity, available=quantity > 0)
    lowered = str(value or "").strip().upper()
    if lowered == "IN_STOCK":
        return Inventory(track_quantity=False, quantity=None, available=True)
    if lowered == "OUT_OF_STOCK":
        return Inventory(track_quantity=False, quantity=None, available=False)
    return Inventory(track_quantity=False, quantity=None, available=True)


def parse_wix_csv(csv_text: str, *, source_weight_unit: str) -> Product:
    headers, rows = csv_rows(csv_text)
    require_headers(headers, _REQUIRED_HEADERS)
    known_headers = set(WIX_COLUMNS)

    handles: list[str] = []
    selected_handle = ""
    for row in rows:
        handle = str(row.get("handle") or "").strip()
        if not handle:
            continue
        if handle not in handles:
            handles.append(handle)
        if not selected_handle:
            selected_handle = handle
    if not selected_handle:
        raise ValueError("Wix CSV must include at least one row with handle.")

    selected_rows = [row for row in rows if str(row.get("handle") or "").strip() == selected_handle]
    product_rows = [row for row in selected_rows if str(row.get("fieldType") or "").strip().upper() == "PRODUCT"]
    product_row = product_rows[0] if product_rows else selected_rows[0]
    variant_rows = [row for row in selected_rows if str(row.get("fieldType") or "").strip().upper() == "VARIANT"]
    media_rows = [row for row in selected_rows if str(row.get("fieldType") or "").strip().upper() == "MEDIA"]

    option_maps: list[dict[str, str]] = []
    variants: list[Variant] = []
    source_rows = variant_rows or [product_row]
    for index, row in enumerate(source_rows, start=1):
        sku = str(row.get("sku") or "").strip() or f"{selected_handle}:{index}"
        option_map: dict[str, str] = {}
        for option_index in range(1, 7):
            name = str(row.get(f"productOptionName{option_index}") or "").strip()
            value = str(row.get(f"productOptionChoices{option_index}") or "").strip()
            if name and value:
                selected = split_tokens(value, sep=";")
                option_map[name] = selected[0] if selected else value
        option_maps.append(option_map)

        weight_grams = weight_to_grams(row.get("weight"), source_weight_unit=source_weight_unit)
        variant = Variant(
            id=str(index),
            sku=sku,
            title=" / ".join(option_map.values()) or None,
            option_values=[{"name": key, "value": value} for key, value in option_map.items()],
            price=price_from_amount(parse_float(row.get("price"))),
            inventory=_variant_inventory_from_wix(str(row.get("inventory") or "")),
            weight=weight_object(weight_grams),
            media=media_from_urls([str(row.get("media") or "").strip()], variant_sku=sku),
            identifiers=Identifiers(values={"source_variant_id": str(index), "sku": sku}),
        )
        apply_extra_variant_fields(variant, row, known_headers=known_headers)
        variants.append(variant)

    media_urls: list[str] = []
    product_media = str(product_row.get("media") or "").strip()
    if product_media:
        media_urls.append(product_media)
    for row in media_rows:
        url = str(row.get("media") or "").strip()
        if url:
            media_urls.append(url)

    product = Product(
        source=SourceRef(platform="wix", id=selected_handle, slug=selected_handle, url=None),
        title=str(product_row.get("name") or "").strip() or None,
        description=str(product_row.get("plainDescription") or "").strip() or None,
        seo=Seo(
            title=str(product_row.get("name") or "").strip() or None,
            description=str(product_row.get("plainDescription") or "").strip() or None,
        ),
        brand=str(product_row.get("brand") or "").strip() or None,
        vendor=str(product_row.get("brand") or "").strip() or None,
        variants=variants,
        options=option_defs_from_option_maps(option_maps),
        price=price_from_amount(parse_float(product_row.get("price"))),
        weight=variants[0].weight,
        requires_shipping=True,
        track_quantity=any(variant.inventory.track_quantity for variant in variants),
        is_digital=False,
        media=media_from_urls(media_urls),
        identifiers=Identifiers(values={"source_product_id": selected_handle}),
    )
    apply_extra_product_fields(product, product_row, known_headers=known_headers)
    add_csv_provenance(
        product,
        source_platform="wix",
        detected_product_count=len(handles),
        selected_product_key=selected_handle,
    )
    return product
