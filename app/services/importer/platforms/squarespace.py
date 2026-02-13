import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from app.models import ProductResult, Variant

from ..product_url_detection import detect_product_url
from .common import (
    ProductClient,
    append_default_variant_if_empty,
    dedupe,
    extract_product_json_ld_nodes,
    http_session,
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


def _extract_names(items: Any) -> list[str]:
    names: list[str] = []
    if isinstance(items, str):
        for token in items.split(","):
            stripped = token.strip()
            if stripped:
                names.append(stripped)
    elif isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    names.append(stripped)
            elif isinstance(item, dict):
                candidate = pick_name(item.get("value")) or pick_name(item.get("name")) or pick_name(item.get("title"))
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
            urls.extend(_extract_image_urls(item))
    elif isinstance(items, dict):
        for key in ("assetUrl", "originalSizeUrl", "imageUrl", "src"):
            normalized = normalize_url(items.get(key))
            if normalized:
                urls.append(normalized)
        if str(items.get("@type") or "").lower() == "imageobject":
            normalized = normalize_url(items.get("url"))
            if normalized:
                urls.append(normalized)
        if items.get("image") is not None:
            urls.extend(_extract_image_urls(items.get("image")))
        if items.get("images") is not None:
            urls.extend(_extract_image_urls(items.get("images")))
    return dedupe(urls)


def _parse_money(raw_value: Any, *, raw_currency: Any = None) -> tuple[float | None, str | None]:
    currency = pick_name(raw_currency)
    if isinstance(raw_value, dict) and not currency:
        currency = pick_name(raw_value.get("currency")) or pick_name(raw_value.get("currencyCode"))

    if isinstance(raw_value, dict):
        for key in ("value", "amount", "price"):
            amount = parse_money_to_float(raw_value.get(key))
            if amount is not None:
                return amount, currency
        return None, currency

    return parse_money_to_float(raw_value), currency


def _offers_to_list(raw_offers: Any) -> list[Any]:
    if isinstance(raw_offers, list):
        return raw_offers
    if isinstance(raw_offers, dict):
        nested = raw_offers.get("offers")
        if isinstance(nested, list):
            return nested
        return [raw_offers]
    return []


def _first_bool(*values: Any) -> bool | None:
    for value in values:
        parsed = to_bool(value)
        if parsed is not None:
            return parsed
    return None


def _parse_offer_variant(raw_offer: Any) -> Variant | None:
    if not isinstance(raw_offer, dict):
        return None

    title = pick_name(raw_offer.get("name")) or pick_name(raw_offer.get("description"))
    sku = pick_name(raw_offer.get("sku"))
    variant_id = pick_name(raw_offer.get("@id")) or pick_name(raw_offer.get("url")) or sku

    raw_price = raw_offer.get("price")
    if raw_price is None and isinstance(raw_offer.get("priceSpecification"), dict):
        raw_price = raw_offer["priceSpecification"].get("price")
    amount, currency = _parse_money(raw_price, raw_currency=raw_offer.get("priceCurrency"))

    availability_text = str(raw_offer.get("availability") or "")
    available = None
    if availability_text:
        lowered = availability_text.lower()
        if "instock" in lowered:
            available = True
        elif "outofstock" in lowered:
            available = False

    options: dict[str, str] = {}
    for option_key in ("color", "size", "material", "pattern"):
        option_value = pick_name(raw_offer.get(option_key))
        if option_value:
            options[option_key.title()] = option_value

    image = None
    images = _extract_image_urls(raw_offer.get("image"))
    if images:
        image = images[0]

    if not any((variant_id, sku, title, amount is not None, available is not None, image, options)):
        return None

    return Variant(
        id=variant_id,
        sku=sku,
        title=title,
        options=options,
        price_amount=amount,
        currency=currency,
        image=image,
        available=available,
    )


def _variant_options_catalog(structured_content: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    raw_variant_options = structured_content.get("variantOptions")
    if not isinstance(raw_variant_options, list):
        return out

    for raw_option in raw_variant_options:
        if not isinstance(raw_option, dict):
            continue
        name = pick_name(raw_option.get("name")) or pick_name(raw_option.get("title"))
        if not name:
            continue

        values = _extract_names(raw_option.get("values"))
        if not values:
            values = _extract_names(raw_option.get("options"))
        if values:
            out[name] = values

    return out


def _parse_variant_options(raw_variant: dict[str, Any], option_names: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}

    raw_option_values = raw_variant.get("optionValues")
    if isinstance(raw_option_values, list):
        for index, raw_value in enumerate(raw_option_values):
            fallback_name = option_names[index] if index < len(option_names) else None
            if isinstance(raw_value, str):
                value = pick_name(raw_value)
                if fallback_name and value:
                    out[fallback_name] = value
                continue

            if not isinstance(raw_value, dict):
                continue

            name = (
                pick_name(raw_value.get("optionName"))
                or pick_name(raw_value.get("name"))
                or pick_name(raw_value.get("label"))
                or fallback_name
            )
            value = pick_name(raw_value.get("value")) or pick_name(raw_value.get("name")) or pick_name(
                raw_value.get("title")
            )
            if name and value:
                out[name] = value
        return out

    if isinstance(raw_option_values, dict):
        for key, value in raw_option_values.items():
            option_name = pick_name(key)
            option_value = pick_name(value)
            if option_name and option_value:
                out[option_name] = option_value
        return out

    for index in range(1, 4):
        value = pick_name(raw_variant.get(f"option{index}"))
        if value:
            name = option_names[index - 1] if index - 1 < len(option_names) else f"Option {index}"
            out[name] = value

    return out


def _fallback_options_from_variants(variants: list[Variant]) -> dict[str, list[str]]:
    if len(variants) <= 1:
        return {}
    values = [
        str(variant.title or variant.sku or variant.id or f"Variant {index}")
        for index, variant in enumerate(variants, start=1)
    ]
    return {"Option": dedupe(values)}


def _variant_product_options(variants: list[Variant]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for variant in variants:
        for name, value in (variant.options or {}).items():
            if not name or not value:
                continue
            out.setdefault(name, []).append(value)
    return {key: dedupe(values) for key, values in out.items() if values}


def _parse_json_ld_product(product_data: dict[str, Any], *, source_url: str, slug: str | None) -> ProductResult:
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
    offer_items = _offers_to_list(raw_offers)
    variants = [variant for variant in (_parse_offer_variant(item) for item in offer_items) if variant]

    default_price = None
    default_currency = "USD"
    for variant in variants:
        if variant.price_amount is not None:
            default_price = variant.price_amount
        if variant.currency:
            default_currency = variant.currency
        if default_price is not None and default_currency:
            break

    if default_price is None and isinstance(raw_offers, dict):
        default_price = parse_money_to_float(raw_offers.get("lowPrice"))
        default_currency = pick_name(raw_offers.get("priceCurrency")) or default_currency

    options = _variant_product_options(variants)
    if not options:
        options = _fallback_options_from_variants(variants)
        if options:
            for index, variant in enumerate(variants, start=1):
                variant.options = {"Option": str(variant.title or variant.sku or variant.id or f"Variant {index}")}
    for variant in variants:
        if variant.image and variant.image not in images:
            images.append(variant.image)

    inferred_slug = slug
    if not inferred_slug:
        info = detect_product_url(source_url)
        inferred_slug = pick_name(info.get("slug")) if isinstance(info, dict) else None

    default_variant = Variant(
        id=(
            pick_name(product_data.get("productID"))
            or pick_name(product_data.get("sku"))
            or pick_name(product_data.get("mpn"))
            or inferred_slug
        ),
        price_amount=default_price,
        currency=default_currency,
        available=True,
    )
    append_default_variant_if_empty(variants, default_variant)

    tags = _extract_names(product_data.get("keywords"))
    category = pick_name(product_data.get("category"))
    meta_title, meta_description = meta_from_description(
        title,
        description,
        strip_html_content=True,
    )

    is_digital = bool(
        to_bool(product_data.get("isDigital"))
        or to_bool(product_data.get("isVirtual"))
        or to_bool(product_data.get("isDownloadable"))
    )

    return ProductResult(
        platform="squarespace",
        id=(
            pick_name(product_data.get("productID"))
            or pick_name(product_data.get("sku"))
            or pick_name(product_data.get("mpn"))
            or inferred_slug
        ),
        title=title,
        description=description,
        price={"amount": default_price, "currency": default_currency},
        images=images,
        options=options,
        variants=variants,
        brand=brand,
        category=category,
        meta_title=meta_title,
        meta_description=meta_description,
        slug=inferred_slug,
        tags=tags,
        vendor=brand,
        weight=None,
        requires_shipping=not is_digital,
        track_quantity=True,
        is_digital=is_digital,
        raw=product_data,
    )


def _iter_dict_nodes(value: Any):
    if isinstance(value, dict):
        yield value
        for nested_value in value.values():
            yield from _iter_dict_nodes(nested_value)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_dict_nodes(item)


def _candidate_score(candidate: dict[str, Any], *, slug: str | None) -> int:
    score = 0
    if isinstance(candidate.get("structuredContent"), dict):
        score += 3
    if pick_name(candidate.get("title")) or pick_name(candidate.get("name")):
        score += 1
    if pick_name(candidate.get("id")):
        score += 1
    if str(pick_name(candidate.get("recordTypeLabel")) or "").lower() == "product":
        score += 2

    url_id = pick_name(candidate.get("urlId"))
    full_url = pick_name(candidate.get("fullUrl"))
    if slug:
        if url_id == slug:
            score += 3
        if isinstance(full_url, str) and f"/{slug}" in full_url:
            score += 2

    return score


def _find_page_json_product(payload: Any, *, slug: str | None) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = 0
    for node in _iter_dict_nodes(payload):
        structured_content = node.get("structuredContent")
        if not isinstance(structured_content, dict):
            continue

        record_type = str(pick_name(node.get("recordTypeLabel")) or "").lower()
        url_id = pick_name(node.get("urlId"))
        has_product_signals = any(
            (
                record_type == "product",
                slug and url_id == slug,
                isinstance(structured_content.get("variants"), list),
                structured_content.get("variantOptions") is not None,
                structured_content.get("priceMoney") is not None,
                pick_name(structured_content.get("productType")) is not None,
            )
        )
        if not has_product_signals:
            continue
        score = _candidate_score(node, slug=slug)
        if score > best_score:
            best = node
            best_score = score
    return best


def _parse_page_json_product(
    candidate: dict[str, Any],
    payload: Any,
    *,
    source_url: str,
    slug: str | None,
) -> ProductResult:
    structured_content = candidate.get("structuredContent") or {}

    title = (
        pick_name(candidate.get("title"))
        or pick_name(candidate.get("name"))
        or pick_name(structured_content.get("title"))
        or ""
    )
    description = (
        pick_name(candidate.get("description"))
        or pick_name(candidate.get("body"))
        or pick_name(structured_content.get("description"))
        or ""
    )

    images: list[str] = []
    images.extend(_extract_image_urls(candidate.get("assetUrl")))
    images.extend(_extract_image_urls(structured_content.get("images")))
    images.extend(_extract_image_urls(structured_content.get("image")))
    images.extend(_extract_image_urls(structured_content.get("items")))
    images = dedupe(images)

    options = _variant_options_catalog(structured_content)
    option_names = list(options.keys())

    variants: list[Variant] = []
    raw_variants = structured_content.get("variants")
    if isinstance(raw_variants, list):
        for index, raw_variant in enumerate(raw_variants, start=1):
            variant_id = None
            title_value = None
            sku = None
            variant_options: dict[str, str] = {}
            amount = None
            currency = None
            available = None
            inventory_quantity = None
            image = None
            has_signal = False

            if isinstance(raw_variant, dict):
                variant_id = pick_name(raw_variant.get("id"))
                title_value = pick_name(raw_variant.get("title")) or pick_name(raw_variant.get("name"))
                sku = pick_name(raw_variant.get("sku"))
                variant_options = _parse_variant_options(raw_variant, option_names)

                amount, currency = _parse_money(raw_variant.get("priceMoney"))
                if amount is None:
                    amount, currency = _parse_money(raw_variant.get("price"))

                available = _first_bool(
                    raw_variant.get("inStock"),
                    raw_variant.get("isInStock"),
                    raw_variant.get("available"),
                )
                inventory_quantity = to_int(raw_variant.get("stock"))
                if inventory_quantity is None:
                    inventory_quantity = to_int(raw_variant.get("quantity"))

                variant_images = _extract_image_urls(raw_variant.get("image"))
                if not variant_images:
                    variant_images = _extract_image_urls(raw_variant.get("images"))
                if variant_images:
                    image = variant_images[0]

                has_signal = any(
                    (
                        variant_id,
                        title_value,
                        sku,
                        amount is not None,
                        available is not None,
                        inventory_quantity is not None,
                        image,
                        variant_options,
                    )
                )
            elif raw_variant is not None:
                variant_id = str(raw_variant)
                has_signal = True

            if not has_signal:
                continue

            variant_key = _slug_token(variant_id or title_value or str(index)) or str(index)
            resolved_sku = sku or f"SQ:{_slug_token(slug or title or candidate.get('id') or 'item')}:{variant_key}"
            variants.append(
                Variant(
                    id=variant_id,
                    sku=resolved_sku,
                    title=title_value,
                    options=variant_options,
                    price_amount=amount,
                    currency=currency,
                    image=image,
                    available=available,
                    inventory_quantity=inventory_quantity,
                )
            )

    default_price = None
    default_currency = "USD"
    for variant in variants:
        if variant.price_amount is not None:
            default_price = variant.price_amount
        if variant.currency:
            default_currency = variant.currency
        if default_price is not None and default_currency:
            break

    if default_price is None:
        default_price, default_currency_candidate = _parse_money(structured_content.get("priceMoney"))
        if default_currency_candidate:
            default_currency = default_currency_candidate

    if not options:
        options = _variant_product_options(variants)
    if not options:
        options = _fallback_options_from_variants(variants)
        if options:
            for index, variant in enumerate(variants, start=1):
                variant.options = {"Option": str(variant.title or variant.sku or variant.id or f"Variant {index}")}
    for variant in variants:
        if variant.image and variant.image not in images:
            images.append(variant.image)

    inferred_slug = slug or pick_name(candidate.get("urlId")) or pick_name(structured_content.get("urlSlug"))
    if not inferred_slug:
        info = detect_product_url(source_url)
        inferred_slug = pick_name(info.get("slug")) if isinstance(info, dict) else None

    default_variant = Variant(
        id=pick_name(candidate.get("id")) or inferred_slug,
        price_amount=default_price,
        currency=default_currency,
        available=True,
    )
    append_default_variant_if_empty(variants, default_variant)

    tags = dedupe(_extract_names(candidate.get("tags")) + _extract_names(structured_content.get("tags")))

    category = None
    categories = _extract_names(candidate.get("categories"))
    if not categories:
        categories = _extract_names(structured_content.get("categories"))
    if categories:
        category = categories[0]

    raw_brand = structured_content.get("brand")
    brand = None
    if isinstance(raw_brand, dict):
        brand = pick_name(raw_brand.get("name"))
    elif isinstance(raw_brand, str):
        brand = pick_name(raw_brand)

    meta_title, meta_description = meta_from_description(
        title,
        description,
        strip_html_content=True,
    )

    is_digital = bool(
        to_bool(structured_content.get("isDigital"))
        or to_bool(structured_content.get("isVirtual"))
        or to_bool(structured_content.get("isDownloadable"))
        or str(structured_content.get("productType") or "").upper() == "DIGITAL"
    )

    return ProductResult(
        platform="squarespace",
        id=pick_name(candidate.get("id")) or inferred_slug,
        title=title,
        description=description,
        price={"amount": default_price, "currency": default_currency},
        images=images,
        options=options,
        variants=variants,
        brand=brand,
        category=category,
        meta_title=meta_title,
        meta_description=meta_description,
        slug=inferred_slug,
        tags=tags,
        vendor=brand,
        weight=None,
        requires_shipping=not is_digital,
        track_quantity=True,
        is_digital=is_digital,
        raw=payload,
    )


def _format_json_url(url: str) -> str:
    parsed = urlparse(url)
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() != "format"
    ]
    query_items.append(("format", "json"))
    return urlunparse(parsed._replace(query=urlencode(query_items)))


class SquarespaceClient(ProductClient):
    platform = "squarespace"

    def __init__(self):
        self._http = http_session()

    def _fetch_from_page_json(self, url: str, *, slug: str | None) -> ProductResult:
        response = self._http.get(
            _format_json_url(url),
            timeout=self._http.request_timeout,
        )
        response.raise_for_status()

        payload = response.json()
        candidate = _find_page_json_product(payload, slug=slug)
        if not candidate:
            raise ValueError("Squarespace page JSON contains no product item with structured content.")

        return _parse_page_json_product(candidate, payload, source_url=url, slug=slug)

    def _fetch_from_html(self, url: str, *, slug: str | None) -> ProductResult:
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

        products = extract_product_json_ld_nodes(response.text)
        if not products:
            raise ValueError("No Product JSON-LD found in Squarespace HTML.")

        selected = products[0]
        if slug:
            for product_data in products:
                product_url = pick_name(product_data.get("url"))
                if product_url and f"/{slug}" in product_url:
                    selected = product_data
                    break

        return _parse_json_ld_product(selected, source_url=url, slug=slug)

    def fetch_product(self, url: str) -> ProductResult:
        info = detect_product_url(url)
        if info.get("platform") != "squarespace":
            raise ValueError("Not a Squarespace URL.")
        if not info.get("is_product"):
            raise ValueError("Squarespace URL is not a product URL.")

        slug = pick_name(info.get("slug"))
        errors: list[Exception] = []

        try:
            return self._fetch_from_page_json(url, slug=slug)
        except (requests.HTTPError, ValueError, requests.RequestException, json.JSONDecodeError) as exc:
            errors.append(exc)

        try:
            return self._fetch_from_html(url, slug=slug)
        except (requests.HTTPError, ValueError, requests.RequestException) as exc:
            errors.append(exc)

        for exc in reversed(errors):
            if isinstance(exc, requests.HTTPError):
                raise exc
        if errors:
            raise ValueError(f"Squarespace import failed: {errors[-1]}")
        raise ValueError("Squarespace import failed.")
