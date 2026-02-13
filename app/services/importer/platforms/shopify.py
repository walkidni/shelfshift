import json
import re
from urllib.parse import urlparse

from app.models import Product, Variant

from ..product_url_detection import extract_shopify_slug_from_path
from .common import (
    ProductClient,
    append_default_variant_if_empty,
    dedupe,
    http_session,
    meta_from_description,
    parse_money_to_float,
)


class ShopifyClient(ProductClient):
    platform = "shopify"

    def __init__(self):
        self._http = http_session()

    def _extract(self, url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        handle = extract_shopify_slug_from_path(parsed.path)
        if not handle:
            raise ValueError("Not a Shopify product path.")
        return parsed.netloc, handle

    def _fetch_from_html(self, url: str) -> Product:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = self._http.get(url, headers=headers, timeout=self._http.request_timeout)
        response.raise_for_status()
        html = response.text

        scripts = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.I | re.S,
        )
        if not scripts:
            raise ValueError("No JSON-LD found in HTML")

        product_ld = None
        for block in scripts:
            try:
                data = json.loads(block.strip())
            except Exception:
                continue

            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "Product":
                        product_ld = item
                        break
            elif data.get("@type") == "Product":
                product_ld = data

            if product_ld:
                break

        if not product_ld:
            raise ValueError("No Product JSON-LD found")

        title = product_ld.get("name", "")
        description = product_ld.get("description", "")

        images = product_ld.get("image") or []
        if isinstance(images, str):
            images = [images]
        images = dedupe(images)

        brand = None
        if isinstance(product_ld.get("brand"), dict):
            brand = product_ld["brand"].get("name")

        offers = product_ld.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}

        price_amount = parse_money_to_float(offers.get("price"))
        currency = offers.get("priceCurrency", "USD")
        available = "InStock" in offers.get("availability", "")
        price = {"amount": price_amount, "currency": currency}

        slug = extract_shopify_slug_from_path(urlparse(url).path)
        variants = [
            Variant(
                id=None,
                title=title,
                price_amount=price_amount,
                currency=currency,
                available=available,
            )
        ]

        return Product(
            platform=self.platform,
            id=None,
            title=title,
            description=description,
            price=price,
            images=images,
            options={},
            variants=variants,
            brand=brand,
            category=product_ld.get("category"),
            meta_title=title,
            meta_description=description[:400].strip() if description else None,
            slug=slug,
            tags=[],
            vendor=brand,
            weight=None,
            requires_shipping=True,
            track_quantity=False,
            is_digital=False,
            raw=product_ld,
        )

    def fetch_product(self, url: str) -> Product:
        host, handle = self._extract(url)
        response = self._http.get(
            f"https://{host}/products/{handle}.json",
            timeout=self._http.request_timeout,
        )
        if response.status_code == 404:
            return self._fetch_from_html(url)

        response.raise_for_status()
        payload = response.json()
        data = payload.get("product", payload)  # some stores might return bare product

        title = data.get("title") or ""
        description = data.get("body_html") or ""

        price_amount = None
        currency = "USD"
        variants_list = data.get("variants", [])
        if variants_list:
            first_variant = variants_list[0]
            price_amount = parse_money_to_float(first_variant.get("price"))
        price = {"amount": price_amount, "currency": currency}

        images = []
        if data.get("images"):
            images = [img.get("src") for img in data["images"] if img.get("src")]
        elif data.get("image") and data["image"].get("src"):
            images = [data["image"]["src"]]
        images = dedupe(images)

        options: dict[str, list[str]] = {}
        variants: list[Variant] = []

        if data.get("options"):
            for option in data["options"]:
                option_name = option.get("name")
                option_values = option.get("values", [])
                if option_name and option_values:
                    options[option_name] = option_values

        if variants_list:
            for variant in variants_list:
                variant_options: dict[str, str] = {}
                if variant.get("option1") and data.get("options") and len(data["options"]) > 0:
                    variant_options[data["options"][0]["name"]] = variant["option1"]
                if variant.get("option2") and data.get("options") and len(data["options"]) > 1:
                    variant_options[data["options"][1]["name"]] = variant["option2"]
                if variant.get("option3") and data.get("options") and len(data["options"]) > 2:
                    variant_options[data["options"][2]["name"]] = variant["option3"]

                inventory_quantity = variant.get("inventory_quantity")
                inventory_quantity = (
                    inventory_quantity if isinstance(inventory_quantity, int) and inventory_quantity >= 0 else 0
                )
                variants.append(
                    Variant(
                        id=str(variant.get("id", "")),
                        sku=(variant.get("sku") or "") + str(variant.get("id") or ""),
                        title=variant.get("title"),
                        options=variant_options,
                        price_amount=parse_money_to_float(variant.get("price")),
                        currency=currency,
                        available=variant.get("available", True),
                        inventory_quantity=inventory_quantity,
                        weight=variant.get("weight"),
                    )
                )

        default_variant = Variant(
            id=str(data.get("id", "")),
            price_amount=price_amount,
            currency=currency,
            available=True,
        )
        append_default_variant_if_empty(variants, default_variant)

        brand = data.get("vendor")
        category = data.get("product_type")

        tags: list[str] = []
        if data.get("tags"):
            tags = [tag.strip() for tag in data["tags"].split(",") if tag.strip()]

        weight = None
        if variants_list and variants_list[0].get("weight"):
            weight = variants_list[0]["weight"]

        meta_title, meta_description = meta_from_description(
            title,
            description,
            strip_html_content=True,
        )

        requires_shipping = True
        track_quantity = True
        is_digital = False
        if category and "digital" in category.lower():
            is_digital = True
            requires_shipping = False
        elif any("digital" in tag.lower() for tag in tags):
            is_digital = True
            requires_shipping = False

        return Product(
            platform=self.platform,
            id=str(data.get("id", "")),
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
            slug=handle,
            tags=tags,
            vendor=brand,
            weight=weight,
            requires_shipping=requires_shipping,
            track_quantity=track_quantity,
            is_digital=is_digital,
            raw=payload,
        )
