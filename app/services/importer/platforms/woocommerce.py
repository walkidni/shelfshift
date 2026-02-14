import json
import re
from typing import Any
from urllib.parse import quote, urlparse

import requests

from app.models import (
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

from ..product_url_detection import detect_product_url, extract_woocommerce_store_api_product_token
from .common import (
    ProductClient,
    append_default_variant_if_empty,
    dedupe,
    extract_product_json_ld_nodes,
    finalize_product_typed_fields,
    http_session,
    make_identifiers,
    make_price,
    meta_from_description,
    normalize_url,
    parse_money_to_float,
    pick_name,
    to_bool,
    to_int,
)


def _slug_token(value: Any) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return token


def _minor_unit(value: Any) -> int:
    parsed = to_int(value)
    if parsed is None:
        return 2
    return max(0, min(parsed, 6))


def _parse_store_api_amount(raw: Any, *, minor_unit_value: int) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return None
        if re.fullmatch(r"-?\d+", stripped):
            return int(stripped) / (10**minor_unit_value)
        return parse_money_to_float(stripped)
    if isinstance(raw, int):
        return raw / (10**minor_unit_value)
    if isinstance(raw, float):
        return raw if not raw.is_integer() else raw / (10**minor_unit_value)
    return parse_money_to_float(raw)


def _parse_price_dict(prices: Any) -> tuple[float | None, str]:
    if not isinstance(prices, dict):
        return None, "USD"
    currency = str(prices.get("currency_code") or prices.get("currency") or "USD").upper()
    mu = _minor_unit(prices.get("currency_minor_unit"))
    for field in ("price", "regular_price", "sale_price"):
        amount = _parse_store_api_amount(prices.get(field), minor_unit_value=mu)
        if amount is not None:
            return amount, currency
    return None, currency


def _parse_price_components(prices: Any) -> tuple[float | None, str, float | None, float | None]:
    if not isinstance(prices, dict):
        return None, "USD", None, None
    currency = str(prices.get("currency_code") or prices.get("currency") or "USD").upper()
    mu = _minor_unit(prices.get("currency_minor_unit"))
    current = _parse_store_api_amount(prices.get("price"), minor_unit_value=mu)
    regular = _parse_store_api_amount(prices.get("regular_price"), minor_unit_value=mu)
    sale = _parse_store_api_amount(prices.get("sale_price"), minor_unit_value=mu)
    if current is None:
        current = regular if regular is not None else sale
    return current, currency, regular, sale


def _extract_names(items: Any) -> list[str]:
    names: list[str] = []
    if isinstance(items, str):
        stripped = items.strip()
        if stripped:
            names.append(stripped)
    elif isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    names.append(stripped)
            elif isinstance(item, dict):
                candidate = pick_name(item.get("name")) or pick_name(item.get("slug")) or pick_name(
                    item.get("value")
                )
                if candidate:
                    names.append(candidate)
    return dedupe(names)


def _extract_image_urls(items: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(items, str):
        normalized = normalize_url(items)
        if normalized:
            urls.append(normalized)
    elif isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                normalized = normalize_url(item)
            elif isinstance(item, dict):
                normalized = normalize_url(item.get("url")) or normalize_url(item.get("src"))
            else:
                normalized = None
            if normalized:
                urls.append(normalized)
    elif isinstance(items, dict):
        normalized = normalize_url(items.get("url")) or normalize_url(items.get("src"))
        if normalized:
            urls.append(normalized)
    return dedupe(urls)


class WooCommerceClient(ProductClient):
    platform = "woocommerce"

    def __init__(self):
        self._http = http_session()

    def _extract_api_product(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            if payload.get("id") is not None and payload.get("name"):
                return payload
            products = payload.get("products")
            if isinstance(products, list):
                for item in products:
                    if isinstance(item, dict) and item.get("id") is not None:
                        return item
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("id") is not None:
                    return item
        raise ValueError("WooCommerce Store API returned no usable product data.")

    def _api_get(self, url: str, *, params: dict[str, Any] | None = None) -> tuple[dict[str, Any], Any]:
        response = self._http.get(
            url,
            params=params,
            timeout=self._http.request_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return self._extract_api_product(payload), payload

    def _store_api_base(self, host: str) -> str:
        return f"https://{host}/wp-json/wc/store/v1/products"

    def _fetch_from_storefront_url(self, storefront_url: str, info: dict[str, Any]) -> tuple[dict[str, Any], Any]:
        parsed = urlparse(storefront_url)
        base_url = self._store_api_base(parsed.netloc)
        product_id = info.get("product_id")
        slug = info.get("slug")
        if product_id:
            return self._api_get(f"{base_url}/{quote(str(product_id), safe='')}")
        if slug:
            return self._api_get(base_url, params={"slug": slug})
        raise ValueError("WooCommerce product URL is missing an id or slug.")

    def _product_key(self, data: dict[str, Any]) -> str:
        for candidate in (data.get("id"), data.get("slug"), data.get("name")):
            token = _slug_token(candidate)
            if token:
                return token
        return "item"

    def _parse_images(self, data: dict[str, Any]) -> list[str]:
        images: list[str] = []
        raw_images = data.get("images")
        if isinstance(raw_images, list):
            for raw_image in raw_images:
                if isinstance(raw_image, str):
                    normalized = normalize_url(raw_image)
                elif isinstance(raw_image, dict):
                    normalized = normalize_url(raw_image.get("src")) or normalize_url(raw_image.get("thumbnail"))
                else:
                    normalized = None
                if normalized:
                    images.append(normalized)
        raw_image = data.get("image")
        if isinstance(raw_image, dict):
            normalized = normalize_url(raw_image.get("src"))
            if normalized:
                images.append(normalized)
        elif isinstance(raw_image, str):
            normalized = normalize_url(raw_image)
            if normalized:
                images.append(normalized)
        return dedupe(images)

    def _parse_options(self, data: dict[str, Any]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        attributes = data.get("attributes")
        if not isinstance(attributes, list):
            return out
        for raw_attribute in attributes:
            if not isinstance(raw_attribute, dict):
                continue
            name = pick_name(raw_attribute.get("name")) or pick_name(raw_attribute.get("attribute"))
            if not name:
                continue
            values = _extract_names(raw_attribute.get("terms"))
            if not values:
                values = _extract_names(raw_attribute.get("options"))
            if not values and raw_attribute.get("option") is not None:
                option_value = pick_name(str(raw_attribute.get("option")))
                values = [option_value] if option_value else []
            if values:
                out[name] = values
        return out

    def _parse_variant_options(self, raw_variant: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        raw_options = raw_variant.get("attributes")
        if isinstance(raw_options, dict):
            for key, value in raw_options.items():
                key_str = pick_name(key)
                value_str = pick_name(value)
                if key_str and value_str:
                    result[key_str] = value_str
            return result
        if not isinstance(raw_options, list):
            return result
        for raw_option in raw_options:
            if not isinstance(raw_option, dict):
                continue
            name = pick_name(raw_option.get("name")) or pick_name(raw_option.get("attribute")) or "Option"
            value = (
                pick_name(raw_option.get("option"))
                or pick_name(raw_option.get("value"))
                or pick_name(raw_option.get("slug"))
            )
            if name and value:
                result[name] = value
        return result

    def _parse_variants(
        self,
        data: dict[str, Any],
        *,
        default_price: float | None,
        default_currency: str,
        default_track_quantity: bool,
        default_allow_backorder: bool | None,
    ) -> list[Variant]:
        raw_variants = data.get("variations")
        if not isinstance(raw_variants, list):
            return []

        parsed: list[Variant] = []
        product_key = self._product_key(data)
        default_available = to_bool(data.get("is_in_stock"))
        for index, raw_variant in enumerate(raw_variants, start=1):
            variant_id: str | None = None
            title: str | None = None
            sku: str | None = None
            options: dict[str, str] = {}
            price_amount = default_price
            currency = default_currency
            available = default_available
            inventory_quantity: int | None = None
            image: str | None = None
            compare_at_price: float | None = None
            track_quantity = default_track_quantity
            allow_backorder = default_allow_backorder
            has_signal = False

            if isinstance(raw_variant, dict):
                if raw_variant.get("id") is not None:
                    variant_id = str(raw_variant.get("id"))
                    has_signal = True
                title = pick_name(raw_variant.get("name")) or pick_name(raw_variant.get("title"))
                if title:
                    has_signal = True
                sku = pick_name(raw_variant.get("sku"))
                if sku:
                    has_signal = True
                options = self._parse_variant_options(raw_variant)
                if options:
                    has_signal = True

                variant_price, variant_currency, regular_price, _sale_price = _parse_price_components(
                    raw_variant.get("prices")
                )
                if variant_price is None:
                    variant_price = parse_money_to_float(raw_variant.get("price"))
                if variant_price is not None:
                    price_amount = variant_price
                    has_signal = True
                compare_at_price = regular_price
                currency = variant_currency or currency

                availability = to_bool(raw_variant.get("is_in_stock"))
                if availability is None:
                    availability = to_bool(raw_variant.get("is_purchasable"))
                if availability is not None:
                    available = availability
                    has_signal = True

                inventory_quantity = to_int(raw_variant.get("stock_quantity"))
                if inventory_quantity is None:
                    inventory_quantity = to_int(raw_variant.get("quantity"))
                if inventory_quantity is not None:
                    has_signal = True
                manage_stock = to_bool(raw_variant.get("manage_stock"))
                if manage_stock is not None:
                    track_quantity = manage_stock
                variant_backorder = to_bool(raw_variant.get("is_on_backorder"))
                if variant_backorder is not None:
                    allow_backorder = variant_backorder

                raw_image = raw_variant.get("image")
                if isinstance(raw_image, dict):
                    image = normalize_url(raw_image.get("src"))
                else:
                    image = normalize_url(raw_image)
                if image:
                    has_signal = True
            elif raw_variant is not None:
                variant_id = str(raw_variant)
                has_signal = True

            if not has_signal:
                continue

            variant_key = _slug_token(variant_id or title or str(index)) or str(index)
            resolved_sku = sku or f"WC:{product_key}:{variant_key}"
            variant_identifiers, variant_typed_identifiers = make_identifiers(
                {
                    "source_variant_id": variant_id,
                    "sku": resolved_sku,
                }
            )
            parsed.append(
                Variant(
                    id=variant_id,
                    sku=resolved_sku,
                    title=title,
                    price=make_price(
                        amount=price_amount,
                        currency=currency or default_currency,
                        compare_at=compare_at_price,
                    ),
                    media=(
                        [
                            Media(
                                url=image,
                                type="image",
                                position=1,
                                is_primary=True,
                                variant_skus=[resolved_sku],
                            )
                        ]
                        if image
                        else []
                    ),
                    option_values=[OptionValue(name=name, value=value) for name, value in options.items()],
                    inventory=Inventory(
                        track_quantity=track_quantity,
                        quantity=inventory_quantity,
                        available=available,
                        allow_backorder=allow_backorder,
                    ),
                    identifiers=variant_identifiers,
                )
            )

        if len(parsed) > 1:
            for index, variant in enumerate(parsed, start=1):
                if not variant.option_values:
                    variant.option_values = [
                        OptionValue(
                            name="Option",
                            value=str(variant.title or variant.sku or variant.id or f"Variant {index}"),
                        )
                    ]

        return parsed

    def _parse_store_api_product(self, data: dict[str, Any], payload: Any, *, source_url: str) -> Product:
        title = pick_name(data.get("name")) or ""
        description = (
            pick_name(data.get("description"))
            or pick_name(data.get("summary"))
            or pick_name(data.get("short_description"))
            or ""
        )
        amount, currency, regular_price, _sale_price = _parse_price_components(data.get("prices"))
        if amount is None:
            amount = parse_money_to_float(data.get("price"))
        options = self._parse_options(data)
        options = [OptionDef(name=name, values=values) for name, values in options.items()]
        manage_stock = to_bool(data.get("manage_stock"))
        track_quantity = manage_stock if manage_stock is not None else True
        allow_backorder = to_bool(data.get("is_on_backorder"))
        variants = self._parse_variants(
            data,
            default_price=amount,
            default_currency=currency,
            default_track_quantity=track_quantity,
            default_allow_backorder=allow_backorder,
        )
        default_variant_identifiers, default_variant_typed_identifiers = make_identifiers(
            {
                "source_variant_id": data.get("id"),
                "sku": data.get("sku"),
            }
        )
        default_variant = Variant(
            id=str(data.get("id")) if data.get("id") is not None else None,
            sku=pick_name(data.get("sku")),
            price=make_price(amount=amount, currency=currency, compare_at=regular_price),
            inventory=Inventory(
                track_quantity=track_quantity,
                quantity=to_int(data.get("stock_quantity")),
                available=to_bool(data.get("is_in_stock")),
                allow_backorder=allow_backorder,
            ),
            identifiers=default_variant_identifiers,
        )
        append_default_variant_if_empty(variants, default_variant)

        brand = pick_name(data.get("brand"))
        if not brand:
            brands = _extract_names(data.get("brands"))
            if brands:
                brand = brands[0]

        category = None
        categories = _extract_names(data.get("categories"))
        if categories:
            category = categories[0]

        tags = _extract_names(data.get("tags"))
        slug = pick_name(data.get("slug"))
        if not slug:
            parsed_permalink = urlparse(pick_name(data.get("permalink")) or "")
            info = detect_product_url(parsed_permalink.geturl()) if parsed_permalink.geturl() else {}
            slug = info.get("slug") if isinstance(info, dict) else None

        product_id = str(data.get("id")) if data.get("id") is not None else None
        meta_title, meta_description = meta_from_description(
            title,
            description,
            strip_html_content=True,
        )

        is_digital = bool(to_bool(data.get("is_downloadable")) or to_bool(data.get("is_virtual")))
        requires_shipping = not is_digital
        image_urls = self._parse_images(data)
        media = [
            Media(
                url=image_url,
                type="image",
                position=index,
                is_primary=(index == 1),
            )
            for index, image_url in enumerate(image_urls, start=1)
        ]
        taxonomy_paths = [[name] for name in categories] if categories else []
        product_identifiers, product_typed_identifiers = make_identifiers(
            {
                "source_product_id": product_id,
                "sku": data.get("sku"),
            }
        )

        return Product(
            title=title,
            description=description,
            variants=variants,
            brand=brand,
            tags=tags,
            vendor=brand,
            weight=None,
            requires_shipping=requires_shipping,
            track_quantity=track_quantity,
            is_digital=is_digital,
            raw=payload,
            price=make_price(
                amount=amount,
                currency=currency,
                compare_at=regular_price,
            ),
            media=media,
            identifiers=product_identifiers,
            seo=Seo(
                title=meta_title,
                description=meta_description,
            ),
            source=SourceRef(
                platform=self.platform,
                id=product_id,
                slug=slug,
                url=source_url,
            ),
            taxonomy=CategorySet(paths=taxonomy_paths, primary=(taxonomy_paths[0] if taxonomy_paths else None)),
        )

    def _parse_html_offer(self, raw_offer: Any) -> Variant | None:
        if not isinstance(raw_offer, dict):
            return None

        raw_price = raw_offer.get("price")
        if raw_price is None and isinstance(raw_offer.get("priceSpecification"), dict):
            raw_price = raw_offer["priceSpecification"].get("price")
        amount = parse_money_to_float(raw_price)
        currency = pick_name(raw_offer.get("priceCurrency")) or "USD"
        availability_text = str(raw_offer.get("availability") or "")
        available = "instock" in availability_text.lower() if availability_text else None
        sku = pick_name(raw_offer.get("sku"))
        variant_id = pick_name(raw_offer.get("@id")) or pick_name(raw_offer.get("url")) or sku

        if not any((variant_id, sku, amount is not None, available is not None)):
            return None

        variant_identifiers, variant_typed_identifiers = make_identifiers(
            {
                "source_variant_id": variant_id,
                "sku": sku,
            }
        )

        return Variant(
            id=variant_id,
            sku=sku,
            price=make_price(amount=amount, currency=currency),
            inventory=Inventory(
                track_quantity=False,
                quantity=None,
                available=available,
            ),
            identifiers=variant_identifiers,
        )

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
        products = extract_product_json_ld_nodes(html)

        if not products:
            raise ValueError("No Product JSON-LD found in WooCommerce HTML.")
        product_data = products[0]

        title = pick_name(product_data.get("name")) or ""
        description = pick_name(product_data.get("description")) or ""
        images = _extract_image_urls(product_data.get("image"))

        brand = None
        raw_brand = product_data.get("brand")
        if isinstance(raw_brand, dict):
            brand = pick_name(raw_brand.get("name"))
        elif isinstance(raw_brand, str):
            brand = pick_name(raw_brand)

        raw_offers = product_data.get("offers")
        offer_items: list[Any]
        if isinstance(raw_offers, list):
            offer_items = raw_offers
        elif raw_offers is None:
            offer_items = []
        else:
            offer_items = [raw_offers]

        variants = [variant for variant in (self._parse_html_offer(item) for item in offer_items) if variant]
        default_price = None
        default_currency = "USD"
        for variant in variants:
            if variant.price and variant.price.current.amount is not None:
                default_price = float(variant.price.current.amount)
            if variant.price and variant.price.current.currency:
                default_currency = variant.price.current.currency
            if default_price is not None and default_currency:
                break

        if default_price is None and isinstance(raw_offers, dict):
            default_price = parse_money_to_float(raw_offers.get("lowPrice"))
            default_currency = pick_name(raw_offers.get("priceCurrency")) or default_currency

        if len(variants) > 1:
            product_key = _slug_token(title) or "item"
            for index, variant in enumerate(variants, start=1):
                if not variant.sku:
                    variant.sku = f"WC:{product_key}:{index}"
                if not variant.option_values:
                    variant.option_values = [
                        OptionValue(
                            name="Option",
                            value=str(variant.title or variant.sku or variant.id or f"Variant {index}"),
                        )
                    ]

        info = detect_product_url(url)
        default_variant = Variant(
            id=(info.get("product_id") or info.get("slug") or _slug_token(title) or None),
            price=make_price(amount=default_price, currency=default_currency),
            inventory=Inventory(
                track_quantity=False,
                quantity=None,
                available=True,
            ),
        )
        append_default_variant_if_empty(variants, default_variant)

        meta_title, meta_description = meta_from_description(
            title,
            description,
            strip_html_content=True,
        )

        product_identifiers, product_typed_identifiers = make_identifiers(
            {
                "source_product_id": info.get("product_id") or info.get("slug"),
            }
        )
        media = [
            Media(
                url=image_url,
                type="image",
                position=index,
                is_primary=(index == 1),
            )
            for index, image_url in enumerate(images, start=1)
        ]
        category_value = pick_name(product_data.get("category"))
        taxonomy_paths = [[category_value]] if category_value else []

        return Product(
            title=title,
            description=description,
            variants=variants,
            brand=brand,
            tags=[],
            vendor=brand,
            weight=None,
            requires_shipping=True,
            track_quantity=True,
            is_digital=False,
            raw=product_data,
            price=make_price(amount=default_price, currency=default_currency),
            media=media,
            identifiers=product_identifiers,
            options=[],
            seo=Seo(
                title=meta_title,
                description=meta_description,
            ),
            source=SourceRef(
                platform=self.platform,
                id=None,
                slug=info.get("slug"),
                url=url,
            ),
            taxonomy=CategorySet(paths=taxonomy_paths, primary=(taxonomy_paths[0] if taxonomy_paths else None)),
        )

    def _fallback_storefront_urls(self, url: str, info: dict[str, Any], *, is_api_url: bool) -> list[str]:
        if not is_api_url:
            return [url]

        parsed = urlparse(url)
        host = parsed.netloc
        urls: list[str] = []

        slug = pick_name(info.get("slug"))
        product_id = pick_name(info.get("product_id"))
        token = extract_woocommerce_store_api_product_token(parsed.path or "")
        if not slug and token and not token.isdigit():
            slug = token
        if not product_id and token and token.isdigit():
            product_id = token

        if slug:
            urls.append(f"https://{host}/product/{slug}/")
        if product_id and product_id.isdigit():
            urls.append(f"https://{host}/?product={product_id}")
        return dedupe(urls)

    def fetch_product(self, url: str) -> Product:
        info = detect_product_url(url)
        if info.get("platform") != "woocommerce":
            raise ValueError("Not a WooCommerce URL.")
        if not info.get("is_product"):
            raise ValueError("WooCommerce URL is not a product URL.")

        parsed = urlparse(url)
        is_api_url = bool(extract_woocommerce_store_api_product_token(parsed.path or ""))
        errors: list[Exception] = []

        try:
            if is_api_url:
                product, payload = self._api_get(url)
            else:
                product, payload = self._fetch_from_storefront_url(url, info)
            parsed_product = self._parse_store_api_product(product, payload, source_url=url)
            return finalize_product_typed_fields(parsed_product, source_url=url)
        except (requests.HTTPError, ValueError, requests.RequestException, json.JSONDecodeError) as exc:
            errors.append(exc)

        for fallback_url in self._fallback_storefront_urls(url, info, is_api_url=is_api_url):
            try:
                parsed_product = self._fetch_from_html(fallback_url)
                return finalize_product_typed_fields(parsed_product, source_url=url)
            except (requests.HTTPError, ValueError, requests.RequestException) as exc:
                errors.append(exc)

        for exc in reversed(errors):
            if isinstance(exc, requests.HTTPError):
                raise exc
        if errors:
            raise ValueError(f"WooCommerce import failed: {errors[-1]}")
        raise ValueError("WooCommerce import failed.")
