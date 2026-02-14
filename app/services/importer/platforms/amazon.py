import re
from urllib.parse import parse_qs, urlparse

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

from ..product_url_detection import _AMAZON_ASIN_RE
from .common import (
    ApiConfig,
    ProductClient,
    append_default_variant_if_empty,
    dedupe,
    finalize_product_typed_fields,
    http_session,
    make_identifiers,
    make_price,
    parse_money_to_float,
)


class AmazonRapidApiClient(ProductClient):
    platform = "amazon"

    def __init__(self, cfg: ApiConfig):
        self.cfg = cfg
        self._http = http_session()

    @staticmethod
    def _guess_country_from_url(url: str) -> str:
        """
        Guess Amazon marketplace country code from the URL domain.
        Defaults to US if no specific match is found.
        """
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()

        if host.endswith("amazon.com"):
            return "US"
        if host.endswith("amazon.ca"):
            return "CA"
        if host.endswith("amazon.com.mx"):
            return "MX"
        if host.endswith("amazon.com.br"):
            return "BR"

        if host.endswith("amazon.co.uk"):
            return "GB"
        if host.endswith("amazon.ie"):
            return "IE"
        if host.endswith("amazon.de"):
            return "DE"
        if host.endswith("amazon.fr"):
            return "FR"
        if host.endswith("amazon.it"):
            return "IT"
        if host.endswith("amazon.es"):
            return "ES"
        if host.endswith("amazon.nl"):
            return "NL"
        if host.endswith("amazon.pl"):
            return "PL"
        if host.endswith("amazon.se"):
            return "SE"
        if host.endswith("amazon.at"):
            return "AT"
        if host.endswith("amazon.com.be"):
            return "BE"
        if host.endswith("amazon.com.tr"):
            return "TR"

        if host.endswith("amazon.co.jp"):
            return "JP"
        if host.endswith("amazon.in"):
            return "IN"
        if host.endswith("amazon.cn"):
            return "CN"
        if host.endswith("amazon.sg"):
            return "SG"
        if host.endswith("amazon.ae"):
            return "AE"
        if host.endswith("amazon.sa"):
            return "SA"
        if host.endswith("amazon.eg"):
            return "EG"
        if host.endswith("amazon.co.za"):
            return "ZA"

        if host.endswith("amazon.com.au"):
            return "AU"

        return "US"

    def _extract_asin(self, url: str) -> str | None:
        parsed = urlparse(url)
        match = _AMAZON_ASIN_RE.search(parsed.path)
        if match:
            return match.group(1)
        query = parse_qs(parsed.query)
        if "asin" in query and query["asin"]:
            return query["asin"][0]
        return None

    def fetch_product(self, url: str) -> Product:
        if not self.cfg.rapidapi_key:
            raise ValueError("RapidAPI key not configured.")
        asin = self._extract_asin(url)
        if not asin:
            raise ValueError("ASIN not found in URL.")
        amazon_country = self._guess_country_from_url(url)

        host = "real-time-amazon-data.p.rapidapi.com"
        endpoint = "/product-details"
        params = {"asin": asin, "country": amazon_country}
        headers = {
            "X-RapidAPI-Key": self.cfg.rapidapi_key,
            "X-RapidAPI-Host": host,
        }

        response = self._http.get(
            f"https://{host}{endpoint}",
            headers=headers,
            params=params,
            timeout=self._http.request_timeout,
        )
        response.raise_for_status()
        resp = response.json()
        data = resp.get("data") or {}

        title = data.get("product_title") or ""
        description = ""
        if data.get("about_product"):
            description = "<br>".join(data["about_product"])
        elif data.get("product_description"):
            description = data["product_description"]

        price_amount = parse_money_to_float(data.get("product_price"))
        currency = data.get("currency", "USD")

        images: list[str] = []
        if data.get("product_photo"):
            images.append(data["product_photo"])
        if data.get("product_photos"):
            images.extend(data["product_photos"])
        if data.get("aplus_images"):
            images.extend(data["aplus_images"])
        images = dedupe(images)

        option_defs: list[OptionDef] = []
        variants: list[Variant] = []

        if data.get("product_variations_dimensions") and data.get("product_variations"):
            for dim in data["product_variations_dimensions"]:
                dim_name = dim.title()
                if dim in data["product_variations"]:
                    values = []
                    for var in data["product_variations"][dim]:
                        if var.get("is_available") and var.get("value"):
                            values.append(var["value"])
                    if values:
                        option_defs.append(OptionDef(name=dim_name, values=dedupe(values)))

            if data.get("all_product_variations"):
                for var_asin, var_options in data["all_product_variations"].items():
                    variant_options = {dim.title(): value for dim, value in var_options.items()}
                    option_values = [OptionValue(name=name, value=value) for name, value in variant_options.items()]
                    is_available = data.get("product_availability", "").lower() == "in stock"
                    if var_asin != asin:
                        for dim in data.get("product_variations_dimensions", []):
                            if dim in data.get("product_variations", {}):
                                for var in data["product_variations"][dim]:
                                    if var.get("asin") == var_asin:
                                        is_available = var.get("is_available", False)
                                        break

                    variant_identifiers = make_identifiers(
                        {
                            "source_variant_id": var_asin,
                            "asin": var_asin,
                        }
                    )

                    variants.append(
                        Variant(
                            id=var_asin,
                            price=make_price(amount=price_amount, currency=currency),
                            option_values=option_values,
                            inventory=Inventory(
                                track_quantity=False,
                                quantity=None,
                                available=is_available,
                            ),
                            identifiers=variant_identifiers,
                        )
                    )

        default_variant = Variant(
            id=asin,
            price=make_price(amount=price_amount, currency=currency),
            inventory=Inventory(
                track_quantity=False,
                quantity=None,
                available=data.get("product_availability", "").lower() == "in stock",
            ),
        )
        append_default_variant_if_empty(variants, default_variant)

        brand = None
        if data.get("product_details") and "Brand" in data["product_details"]:
            brand = data["product_details"]["Brand"]
        elif data.get("product_information") and "Manufacturer" in data["product_information"]:
            brand = data["product_information"]["Manufacturer"]
        if not brand and data.get("product_byline"):
            byline = data["product_byline"]
            if byline.startswith("Visit the ") and byline.endswith(" Store"):
                brand = byline[10:-6]

        meta_title = title
        meta_description = data["customers_say"][:400] if data.get("customers_say") else None
        slug = data.get("product_slug", "")

        tags: list[str] = []
        if data.get("product_information"):
            info = data["product_information"]
            if info.get("Special features"):
                tags.append(info["Special features"])
            if info.get("Compatible Devices"):
                tags.extend([device.strip() for device in info["Compatible Devices"].split(",")])

        weight = None
        if data.get("product_information") and "Item Weight" in data["product_information"]:
            weight_str = data["product_information"]["Item Weight"]
            try:
                weight_match = re.search(r"([\d.]+)", weight_str)
                if weight_match:
                    weight_val = float(weight_match.group(1))
                    if "ounce" in weight_str.lower():
                        weight = weight_val * 28.35
                    else:
                        weight = weight_val
            except (ValueError, AttributeError):
                pass

        taxonomy_paths: list[list[str]] = []
        category_path = data.get("category_path")
        if isinstance(category_path, list):
            names = [entry.get("name") for entry in category_path if isinstance(entry, dict) and entry.get("name")]
            if names:
                taxonomy_paths.append(names)

        product_identifiers = make_identifiers(
            {
                "source_product_id": asin,
                "asin": asin,
                "parent_asin": data.get("parent_asin"),
                "landing_asin": data.get("landing_asin"),
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
            requires_shipping=True,
            track_quantity=True,
            is_digital=False,
            raw=resp,
            price=make_price(
                amount=price_amount,
                currency=currency,
                compare_at=data.get("product_original_price"),
            ),
            media=[
                Media(
                    url=image_url,
                    type="image",
                    position=index,
                    is_primary=(index == 1),
                )
                for index, image_url in enumerate(images, start=1)
            ],
            options=option_defs,
            identifiers=product_identifiers,
            seo=Seo(
                title=meta_title,
                description=meta_description,
            ),
            source=SourceRef(
                platform=self.platform,
                id=asin,
                slug=slug,
                url=url,
            ),
            taxonomy=CategorySet(paths=taxonomy_paths, primary=(taxonomy_paths[0] if taxonomy_paths else None)),
        )
        return finalize_product_typed_fields(product, source_url=url)
