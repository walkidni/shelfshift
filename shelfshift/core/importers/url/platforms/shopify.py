import json
import re
from urllib.parse import urlparse

from ....canonical import (
    CategorySet,
    Inventory,
    Media,
    OptionDef,
    OptionValue,
    Product,
    Seo,
    SourceRef,
    Variant,
)

from ....detect.url import extract_shopify_slug_from_path
from ..common import (
    ProductClient,
    append_default_variant_if_empty,
    dedupe,
    finalize_product_typed_fields,
    http_session,
    make_identifiers,
    make_price,
    meta_from_description,
    normalize_url,
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

    def _product_media_from_images(self, raw_images: list[dict], sku_by_variant_id: dict[str, str]) -> list[Media]:
        media: list[Media] = []
        for raw_image in raw_images:
            if not isinstance(raw_image, dict):
                continue
            image_url = normalize_url(raw_image.get("src"))
            if not image_url:
                continue
            raw_variant_ids = raw_image.get("variant_ids")
            variant_skus: list[str] = []
            if isinstance(raw_variant_ids, list):
                for raw_variant_id in raw_variant_ids:
                    variant_sku = sku_by_variant_id.get(str(raw_variant_id))
                    if variant_sku:
                        variant_skus.append(variant_sku)
            media.append(
                Media(
                    url=image_url,
                    type="image",
                    alt=(raw_image.get("alt") or None),
                    position=(raw_image.get("position") if isinstance(raw_image.get("position"), int) else None),
                    is_primary=(raw_image.get("position") == 1),
                    variant_skus=variant_skus,
                )
            )
        return media

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
        slug = extract_shopify_slug_from_path(urlparse(url).path)
        variants = [
            Variant(
                id=None,
                title=title,
                price=make_price(amount=price_amount, currency=currency),
                inventory=Inventory(track_quantity=False, quantity=None, available=available),
            )
        ]
        product = Product(
            title=title,
            description=description,
            variants=variants,
            brand=brand,
            tags=[],
            vendor=brand,
            weight=None,
            requires_shipping=True,
            track_quantity=False,
            is_digital=False,
            raw=product_ld,
            price=make_price(amount=price_amount, currency=currency),
            media=[
                Media(
                    url=image_url,
                    type="image",
                    position=index,
                    is_primary=(index == 1),
                )
                for index, image_url in enumerate(images, start=1)
            ],
            options=[],
            seo=Seo(
                title=title,
                description=description[:400].strip() if description else None,
            ),
            source=SourceRef(
                platform=self.platform,
                id=None,
                slug=slug,
                url=url,
            ),
            taxonomy=(
                CategorySet(paths=[[str(product_ld.get("category"))]], primary=[str(product_ld.get("category"))])
                if product_ld.get("category")
                else CategorySet()
            ),
        )
        product.identifiers = make_identifiers({})
        return product

    def fetch_product(self, url: str) -> Product:
        host, handle = self._extract(url)
        response = self._http.get(
            f"https://{host}/products/{handle}.json",
            timeout=self._http.request_timeout,
        )
        if response.status_code == 404:
            return finalize_product_typed_fields(self._fetch_from_html(url), source_url=url)

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
            currency = (first_variant.get("price_currency") or currency)
        images = []
        if data.get("images"):
            images = [img.get("src") for img in data["images"] if img.get("src")]
        elif data.get("image") and data["image"].get("src"):
            images = [data["image"]["src"]]
        images = dedupe(images)

        option_defs: list[OptionDef] = []
        variants: list[Variant] = []

        if data.get("options"):
            for option in data["options"]:
                option_name = option.get("name")
                option_values = option.get("values", [])
                if option_name and option_values:
                    option_defs.append(OptionDef(name=option_name, values=option_values))

        sku_by_variant_id: dict[str, str] = {}
        for variant in variants_list:
            raw_variant_id = variant.get("id")
            raw_sku = (variant.get("sku") or "").strip()
            if raw_variant_id is not None and raw_sku:
                sku_by_variant_id[str(raw_variant_id)] = raw_sku

        image_by_id: dict[str, dict] = {}
        for raw_image in (data.get("images") or []):
            if isinstance(raw_image, dict) and raw_image.get("id") is not None:
                image_by_id[str(raw_image.get("id"))] = raw_image

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
                variant_id = str(variant.get("id", ""))
                raw_sku = (variant.get("sku") or "").strip()
                compare_at_amount = parse_money_to_float(variant.get("compare_at_price"))
                inventory_management = str(variant.get("inventory_management") or "").strip().lower()
                track_inventory = bool(inventory_management and inventory_management != "null")
                inventory_policy = str(variant.get("inventory_policy") or "").strip().lower()
                allow_backorder = True if inventory_policy == "continue" else False if inventory_policy else None
                variant_image_raw = image_by_id.get(str(variant.get("image_id")))
                variant_media: list[Media] = []
                if isinstance(variant_image_raw, dict):
                    variant_image_url = normalize_url(variant_image_raw.get("src"))
                    if variant_image_url:
                        variant_media.append(
                            Media(
                                url=variant_image_url,
                                type="image",
                                alt=(variant_image_raw.get("alt") or None),
                                position=1,
                                is_primary=True,
                                variant_skus=[raw_sku] if raw_sku else [],
                            )
                        )

                variant_identifiers = make_identifiers(
                    {
                        "source_variant_id": variant_id,
                        "sku": raw_sku,
                        "barcode": variant.get("barcode"),
                    }
                )
                variants.append(
                    Variant(
                        id=variant_id,
                        sku=(variant.get("sku") or "") + str(variant.get("id") or ""),
                        title=variant.get("title"),
                        weight=variant.get("weight"),
                        price=make_price(
                            amount=variant.get("price"),
                            currency=(variant.get("price_currency") or currency),
                            compare_at=compare_at_amount,
                        ),
                        media=variant_media,
                        option_values=[OptionValue(name=name, value=value) for name, value in variant_options.items()],
                        inventory=Inventory(
                            track_quantity=track_inventory,
                            quantity=inventory_quantity,
                            available=variant.get("available", True),
                            allow_backorder=allow_backorder,
                        ),
                        identifiers=variant_identifiers,
                    )
                )

        default_variant = Variant(
            id=str(data.get("id", "")),
            price=make_price(amount=price_amount, currency=currency),
            inventory=Inventory(track_quantity=False, quantity=None, available=True),
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

        product_media = self._product_media_from_images(data.get("images") or [], sku_by_variant_id)
        if not product_media and isinstance(data.get("image"), dict):
            image_url = normalize_url(data["image"].get("src"))
            if image_url:
                product_media = [
                    Media(
                        url=image_url,
                        type="image",
                        alt=(data["image"].get("alt") or None),
                        position=(data["image"].get("position") if isinstance(data["image"].get("position"), int) else 1),
                        is_primary=True,
                    )
                ]

        product_identifiers = make_identifiers(
            {
                "source_product_id": data.get("id"),
                "handle": handle,
            }
        )

        product = Product(
            title=title,
            description=description,
            variants=variants,
            brand=brand,
            tags=tags,
            vendor=brand,
            weight=weight,
            requires_shipping=requires_shipping,
            track_quantity=track_quantity,
            is_digital=is_digital,
            raw=payload,
            price=make_price(
                amount=price_amount,
                currency=currency,
                compare_at=parse_money_to_float(variants_list[0].get("compare_at_price")) if variants_list else None,
            ),
            media=product_media,
            identifiers=product_identifiers,
            options=option_defs,
            seo=Seo(
                title=meta_title,
                description=meta_description,
            ),
            source=SourceRef(
                platform=self.platform,
                id=str(data.get("id", "")),
                slug=handle,
                url=url,
            ),
            taxonomy=CategorySet(paths=[[category]], primary=[category]) if category else CategorySet(),
        )
        return finalize_product_typed_fields(product, source_url=url)
