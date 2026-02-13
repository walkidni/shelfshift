import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from app.models import Product, Variant

from ..product_url_detection import _ALIEXPRESS_ITEM_RE, _ALIEXPRESS_X_OBJECT_RE
from .common import (
    ApiConfig,
    ProductClient,
    append_default_variant_if_empty,
    dedupe,
    http_session,
    meta_from_description,
    parse_money_to_float,
)


def _parse_aliexpress_result(resp: dict, item_id: str) -> Product:
    result = resp.get("result", {}) if isinstance(resp, dict) else {}
    item = result.get("item", {}) if isinstance(result, dict) else {}

    title = item.get("title") or ""
    description = ""
    if item.get("description") and item["description"].get("html"):
        description = item["description"]["html"]

    sku_data = item.get("sku", {})
    sku_def = sku_data.get("def", {})

    price_amount = None
    currency = (
        result.get("settings", {}).get("currency")
        if isinstance(result.get("settings"), dict)
        else None
    ) or "USD"

    if sku_def.get("promotionPrice") is not None:
        price_str = str(sku_def["promotionPrice"]).replace("$", "").split(" - ")[0]
        price_amount = parse_money_to_float(price_str)
    elif sku_def.get("price") is not None:
        price_str = str(sku_def["price"]).replace("$", "").split(" - ")[0]
        price_amount = parse_money_to_float(price_str)

    price = {"amount": price_amount, "currency": currency}

    def normalize_url(value: Any) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        if value.startswith("//"):
            return f"https:{value}"
        return value

    images: list[str] = []
    for raw_img in item.get("images", []) or []:
        normalized = normalize_url(raw_img)
        if normalized:
            images.append(normalized)
    images = dedupe(images)

    options: dict[str, list[str]] = {}
    variants: list[Variant] = []

    prop_lookup: dict[int, dict[str, Any]] = {}
    for prop in sku_data.get("props", []) or []:
        prop_name = prop.get("name")
        prop_values = prop.get("values") or []
        if not prop_name or not prop_values:
            continue

        option_values = [val.get("name") for val in prop_values if val.get("name")]
        if option_values:
            options[prop_name] = option_values

        pid_raw = prop.get("pid")
        try:
            pid = int(pid_raw)
        except (TypeError, ValueError):
            continue

        values_by_vid: dict[int, dict[str, Any]] = {}
        for val in prop_values:
            vid_raw = val.get("vid")
            try:
                vid = int(vid_raw)
            except (TypeError, ValueError):
                continue
            values_by_vid[vid] = val

        prop_lookup[pid] = {"name": prop_name, "values": values_by_vid}

    sku_images = sku_data.get("skuImages", {}) if isinstance(sku_data.get("skuImages"), dict) else {}

    for sku in sku_data.get("base", []) or []:
        variant_options: dict[str, str] = {}
        variant_image: str | None = None

        prop_map = str(sku.get("propMap") or "")
        for pair in (prop_map.split(";") if prop_map else []):
            if ":" not in pair:
                continue
            pid_str, vid_str = pair.split(":", 1)
            try:
                pid = int(pid_str)
                vid = int(vid_str)
            except ValueError:
                continue

            prop_data = prop_lookup.get(pid)
            if not prop_data:
                continue

            prop_name = prop_data["name"]
            val = prop_data["values"].get(vid)
            if not val:
                continue

            value_name = val.get("name")
            if isinstance(value_name, str) and value_name:
                variant_options[prop_name] = value_name

            if not variant_image:
                map_key = f"{pid}:{vid}"
                image_candidate = sku_images.get(map_key) or val.get("image")
                variant_image = normalize_url(image_candidate)

        variant_price = price_amount
        if sku.get("promotionPrice") is not None:
            variant_price = parse_money_to_float(str(sku["promotionPrice"]).replace("$", ""))
        elif sku.get("price") is not None:
            variant_price = parse_money_to_float(str(sku["price"]).replace("$", ""))

        quantity_raw = sku.get("quantity", 0)
        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            quantity = 0
        available = quantity > 0

        sku_id = str(sku.get("skuId") or "").strip()
        canonical_sku = f"AE:{item_id}:{sku_id}" if sku_id else None

        variants.append(
            Variant(
                id=sku_id or None,
                sku=canonical_sku,
                options=variant_options,
                price_amount=variant_price,
                currency=currency,
                available=available,
                inventory_quantity=quantity,
                image=variant_image,
            )
        )

        if variant_image and variant_image not in images:
            images.append(variant_image)

    default_variant = None
    if price_amount is not None:
        default_variant = Variant(
            id=str(item_id),
            price_amount=price_amount,
            currency=currency,
            available=item.get("available", True),
        )
    append_default_variant_if_empty(variants, default_variant)

    properties = item.get("properties", {})
    prop_list = properties.get("list", []) if properties else []

    brand = None
    weight_grams: int | None = None
    category = "Electronics"

    def parse_weight_to_grams(raw_value: Any) -> int | None:
        if raw_value is None:
            return None
        text = str(raw_value).strip()
        if not text:
            return None
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
        if not match:
            return None
        try:
            value = float(match.group(1))
        except ValueError:
            return None

        lowered = text.lower()
        if "kg" in lowered:
            return int(round(value * 1000))
        if " g" in lowered or lowered.endswith("g"):
            return int(round(value))
        if 0 < value <= 50:
            return int(round(value * 1000))
        return int(round(value))

    for prop in prop_list:
        prop_name = str(prop.get("name") or "").strip()
        prop_value = str(prop.get("value") or "").strip()
        if not prop_name or not prop_value:
            continue

        name_lower = prop_name.lower()
        if name_lower in {"brand name", "brand"}:
            brand = prop_value
        elif name_lower == "type":
            category = prop_value
        elif name_lower == "weight" and weight_grams is None:
            weight_grams = parse_weight_to_grams(prop_value)

    vendor = None
    if result.get("seller") and result["seller"].get("storeTitle"):
        vendor = result["seller"]["storeTitle"]

    if weight_grams is None and result.get("delivery") and result["delivery"].get("packageDetail"):
        package = result["delivery"]["packageDetail"]
        weight_grams = parse_weight_to_grams(package.get("weight"))

    weight = float(weight_grams) if weight_grams is not None else None
    slug = f"aliexpress-{item_id}"
    meta_title, meta_description = meta_from_description(
        title,
        description if len(description) > 160 else None,
        strip_html_content=True,
    )

    return Product(
        platform="aliexpress",
        id=str(item_id),
        title=title,
        description=description,
        price=price,
        images=images,
        options=options,
        variants=variants,
        brand=brand,
        category=category,
        meta_title=meta_title,
        meta_description=meta_description,
        slug=slug,
        vendor=vendor,
        weight=weight,
        requires_shipping=True,
        track_quantity=True,
        is_digital=False,
        raw=resp,
    )


class AliExpressClient(ProductClient):
    platform = "aliexpress"

    def __init__(self, cfg: ApiConfig):
        self.cfg = cfg
        self._http = http_session()

    def _extract_item_id(self, url: str) -> str | None:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        for values in query.values():
            for v in values:
                match = _ALIEXPRESS_X_OBJECT_RE.search(v)
                if match:
                    return match.group(1)

                decoded = unquote(v)
                match = _ALIEXPRESS_X_OBJECT_RE.search(decoded)
                if match:
                    return match.group(1)

        match = _ALIEXPRESS_ITEM_RE.search(parsed.path)
        if match:
            return match.group(1)

        return None

    def fetch_product(self, url: str) -> Product:
        if not self.cfg.rapidapi_key:
            raise ValueError("RapidAPI key not configured for AliExpress.")
        item_id = self._extract_item_id(url)
        if not item_id:
            raise ValueError("AliExpress item_id not found in URL.")

        host = "aliexpress-datahub.p.rapidapi.com"
        params = {"itemId": item_id}
        headers = {
            "X-RapidAPI-Key": self.cfg.rapidapi_key,
            "X-RapidAPI-Host": host,
        }

        def _call(endpoint: str) -> dict:
            response = self._http.get(
                f"https://{host}{endpoint}",
                headers=headers,
                params=params,
                timeout=self._http.request_timeout,
            )
            response.raise_for_status()
            return response.json()

        resp = _call("/item_detail_6")
        result = resp.get("result", {}) if isinstance(resp, dict) else {}
        item = result.get("item", {}) if isinstance(result, dict) else {}

        if not item or not item.get("title"):
            try:
                fallback_resp = _call("/item_detail_2")
                fallback_result = fallback_resp.get("result", {}) if isinstance(fallback_resp, dict) else {}
                fallback_item = fallback_result.get("item", {}) if isinstance(fallback_result, dict) else {}
                if fallback_item and fallback_item.get("title"):
                    resp = fallback_resp
            except Exception:
                pass

        return _parse_aliexpress_result(resp, item_id)
