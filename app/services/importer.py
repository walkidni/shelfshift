from __future__ import annotations

import re
import json
import typing as t
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs, unquote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ----------------------------- HTTP helper -----------------------------
def http_session(timeout: int = 20) -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    # store desired default timeout on the session for convenience
    s.request_timeout = timeout  # type: ignore[attr-defined]
    return s


# ----------------------------- Detection regexes -----------------------------
_AMAZON_ASIN_RE = re.compile(r"/(?:gp/product|dp)/([A-Z0-9]{10})(?:[/?#]|$)", re.I)
_ETSY_LISTING_RE = re.compile(r"^/listing/(\d+)(?:[/-]|$)", re.I)
_ALIEXPRESS_ITEM_RE = re.compile(r"/(?:item|i)/(\d+)\.html(?:[/?#]|$)", re.I)
_ALIEXPRESS_X_OBJECT_RE = re.compile(
    r"x_object_id(?:%25)?(?:%3A|%3D|:|=)(\d{12,20})",
    re.I
)

# _SHOPIFY_PRODUCT_RE = re.compile(r"^/(?:collections/[^/]+/)?products/([^/?#]+)(?:[/?#]|$)", re.I)
# _SHOPIFY_PRODUCT_RE = re.compile(
#     r"^/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:collections/[^/]+/)?products/([^/?#]+)(?:[/?#]|$)",
#     re.I
# )
_SHOPIFY_PRODUCT_RE = re.compile(
    r"^/(?:[a-z]{2}(?:-[a-z0-9]{2,8})?/)?(?:collections/[^/]+/)?products/([^/?#]+)(?:[/?#]|$)",
    re.I
)


def detect_product_url(url: str) -> dict:
    """
    Returns: {'platform', 'is_product', 'product_id', 'slug'}
    """
    res = {'platform': None, 'is_product': False, 'product_id': None, 'slug': None}
    try:
        p = urlparse(url)
    except Exception:
        return res
    host = (p.netloc or "").lower()

    if "amazon." in host:
        m = _AMAZON_ASIN_RE.search(p.path)
        if m:
            res.update(platform="amazon", is_product=True, product_id=m.group(1)); return res
        qs = parse_qs(p.query)
        for key in ("asin", "ASIN"):
            if key in qs and qs[key] and re.fullmatch(r"[A-Z0-9]{10}", qs[key][0], re.I):
                res.update(platform="amazon", is_product=True, product_id=qs[key][0]); return res
        res.update(platform="amazon"); return res

    if "etsy.com" in host:
        m = _ETSY_LISTING_RE.search(p.path)
        if m:
            res.update(platform="etsy", is_product=True, product_id=m.group(1)); return res
        qs = parse_qs(p.query)
        if "listing_id" in qs and qs["listing_id"]:
            res.update(platform="etsy", is_product=True, product_id=qs["listing_id"][0]); return res
        res.update(platform="etsy"); return res

    if "aliexpress." in host:
        m = _ALIEXPRESS_ITEM_RE.search(p.path)
        if m:
            res.update(platform="aliexpress", is_product=True, product_id=m.group(1)); return res
        res.update(platform="aliexpress"); return res

    if host.endswith(".myshopify.com") or _SHOPIFY_PRODUCT_RE.search(p.path):
        m = _SHOPIFY_PRODUCT_RE.search(p.path)
        if m:
            res.update(platform="shopify", is_product=True, slug=m.group(1)); return res
        res.update(platform="shopify"); return res

    return res


# ----------------------------- Shared structures -----------------------------
@dataclass
class Variant:
    id: t.Optional[str] = None
    sku: t.Optional[str] = None
    title: t.Optional[str] = None
    options: dict[str, str] = None  # e.g. {"Color": "Black", "Size": "M"}
    price_amount: t.Optional[float] = None
    currency: t.Optional[str] = None
    image: t.Optional[str] = None
    available: t.Optional[bool] = None
    inventory_quantity: t.Optional[int] = None
    weight: t.Optional[float] = None  # For shipping calculations
    raw: t.Optional[dict] = None

    def __post_init__(self):
        if self.options is None:
            self.options = {}

    def to_dict(self, include_raw: bool = True) -> dict:
        data = {
            "id": self.id,
            "sku": self.sku,
            "title": self.title,
            "options": self.options or {},
            "price_amount": self.price_amount,
            "currency": self.currency,
            "image": self.image,
            "available": self.available,
            "inventory_quantity": self.inventory_quantity,
            "weight": self.weight,
        }
        if include_raw:
            data["raw"] = self.raw
        return data


@dataclass
class ProductResult:
    platform: str
    id: t.Optional[str]
    title: t.Optional[str]
    description: t.Optional[str]
    price: t.Optional[dict]     # {"amount": float|None, "currency": str|None} (typically min/current)
    images: t.List[str]
    raw: t.Optional[dict]
    options: dict[str, t.List[str]]  = None  # {"Color": ["Black","White"], "Size": ["S","M"]}
    variants: t.List[Variant] = None
    brand: t.Optional[str] = None  # Product brand for metadata
    category: t.Optional[str] = None  # Product category for SEO and organization
    meta_title: t.Optional[str] = None  # Custom page title for SEO
    meta_description: t.Optional[str] = None  # Custom meta description for SEO
    slug: t.Optional[str] = None  # Source URL slug if available
    tags: t.List[str] = None  # Tags for searchability
    vendor: t.Optional[str] = None  # Vendor/supplier name
    weight: t.Optional[float] = None  # Default product weight
    requires_shipping: bool = True  # Whether product needs shipping
    track_quantity: bool = True  # Whether to track inventory
    is_digital: bool = False  # Digital product flag

    def __post_init__(self):
        if self.options is None:
            self.options = {}
        if self.variants is None:
            self.variants = []
        if self.images is None:
            self.images = []
        if self.tags is None:
            self.tags = []

    def to_dict(self, include_raw: bool = True) -> dict:
        data = {
            "platform": self.platform,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "images": self.images,
            "options": self.options or {},
            "variants": [v.to_dict(include_raw=include_raw) for v in (self.variants or [])],
            "brand": self.brand,
            "category": self.category,
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "slug": self.slug,
            "tags": self.tags or [],
            "vendor": self.vendor,
            "weight": self.weight,
            "requires_shipping": self.requires_shipping,
            "track_quantity": self.track_quantity,
            "is_digital": self.is_digital,
        }
        if include_raw:
            data["raw"] = self.raw
        return data


class ProductClient:
    platform: str = "generic"
    def fetch_product(self, url: str) -> ProductResult:
        raise NotImplementedError


@dataclass
class ApiConfig:
    """
    Minimal configuration for RapidAPI-backed clients.
    Hosts/endpoints are hardcoded in the clients.
    """
    rapidapi_key: t.Optional[str] = None
    amazon_country: str = "US"  # used by the Amazon provider


# ----------------------------- helpers used in clients -----------------------------
def _dedupe(seq: t.Iterable[str]) -> t.List[str]:
    seen = set()
    out: t.List[str] = []
    for x in seq:
        if isinstance(x, str) and x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _parse_money_to_float(x: t.Any) -> t.Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        try:
            return float(x)
        except Exception:
            return None
    if isinstance(x, str):
        s = x.strip()
        s = s.replace(",", "")
        s = re.sub(r"[^\d\.]", "", s)  # drop currency symbols/letters
        try:
            return float(s) if s else None
        except Exception:
            return None
    return None


# ----------------------------- Shopify (public JSON) -----------------------------
class ShopifyClient(ProductClient):
    platform = "shopify"

    def __init__(self):
        self._http = http_session()
    def _extract(self, url: str) -> t.Tuple[str, str]:
        p = urlparse(url)
        m = _SHOPIFY_PRODUCT_RE.search(p.path)
        if not m:
            raise ValueError("Not a Shopify product path.")
        return p.netloc, m.group(1)
    
    def _fetch_from_html(self, url: str) -> ProductResult:
        HEADERS = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        r = self._http.get(url, headers=HEADERS, timeout=self._http.request_timeout)
        r.raise_for_status()
        html = r.text

        # 1️⃣ Extract JSON-LD blocks
        scripts = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.I | re.S
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

        # 2️⃣ Extract core fields
        title = product_ld.get("name", "")
        description = product_ld.get("description", "")

        images = product_ld.get("image") or []
        if isinstance(images, str):
            images = [images]
        images = _dedupe(images)

        brand = None
        if isinstance(product_ld.get("brand"), dict):
            brand = product_ld["brand"].get("name")

        # 3️⃣ Offers (price, currency, availability)
        offers = product_ld.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}

        price_amount = _parse_money_to_float(offers.get("price"))
        currency = offers.get("priceCurrency", "USD")

        availability_url = offers.get("availability", "")
        available = "InStock" in availability_url

        price = {
            "amount": price_amount,
            "currency": currency,
        }

        # 4️⃣ Slug
        path = urlparse(url).path
        slug_match = re.search(r"/products/([^/?#]+)", path, re.I)
        slug = slug_match.group(1) if slug_match else None

        # 5️⃣ Variant (JSON-LD is usually single-offer)
        variants = [
            Variant(
                id=None,
                title=title,
                price_amount=price_amount,
                currency=currency,
                available=available,
            )
        ]

        # 6️⃣ Meta
        meta_title = title
        meta_description = description[:400].strip() if description else None

        return ProductResult(
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
            meta_title=meta_title,
            meta_description=meta_description,
            slug=slug,
            tags=[],
            vendor=brand,
            weight=None,
            requires_shipping=True,
            track_quantity=False,
            is_digital=False,
            raw=product_ld,
        )


    def fetch_product(self, url: str) -> ProductResult:
        host, handle = self._extract(url)
        r = self._http.get(f"https://{host}/products/{handle}.json", timeout=self._http.request_timeout)
        if r.status_code == 404:
            return self._fetch_from_html(url)

        r.raise_for_status()
        payload = r.json()
        data = payload.get("product", payload)  # some stores might return bare product

        # Extract basic product information
        title = data.get("title") or ""
        description = data.get("body_html") or ""

        # Extract pricing from variants
        price_amount = None
        currency = "USD"  # Default currency
        variants_list = data.get("variants", [])
        if variants_list:
            # Use the first variant's price as base price
            first_variant = variants_list[0]
            price_amount = _parse_money_to_float(first_variant.get("price"))
        
        price = {"amount": price_amount, "currency": currency}

        # Extract images
        images = []
        if data.get("images"):
            images = [img.get("src") for img in data["images"] if img.get("src")]
        elif data.get("image") and data["image"].get("src"):
            images = [data["image"]["src"]]
        images = _dedupe(images)

        # Extract options and variants
        options = {}
        variants = []
        
        if data.get("options"):
            for option in data["options"]:
                option_name = option.get("name")
                option_values = option.get("values", [])
                if option_name and option_values:
                    options[option_name] = option_values

        if variants_list:
            for variant in variants_list:
                variant_options = {}
                
                # Map option values to option names
                if variant.get("option1") and data.get("options") and len(data["options"]) > 0:
                    variant_options[data["options"][0]["name"]] = variant["option1"]
                if variant.get("option2") and data.get("options") and len(data["options"]) > 1:
                    variant_options[data["options"][1]["name"]] = variant["option2"]
                if variant.get("option3") and data.get("options") and len(data["options"]) > 2:
                    variant_options[data["options"][2]["name"]] = variant["option3"]

                variant_price = _parse_money_to_float(variant.get("price"))
                available = variant.get("available", True)
                inventory_quantity = variant.get("inventory_quantity")
                inventory_quantity = inventory_quantity if isinstance(inventory_quantity, int) and inventory_quantity >= 0 else 0
                
                variants.append(Variant(
                    id=str(variant.get("id", "")),
                    sku=(variant.get("sku") or "") + str(variant.get("id") or ""),
                    title=variant.get("title"),
                    options=variant_options,
                    price_amount=variant_price,
                    currency=currency,
                    available=available,
                    inventory_quantity=inventory_quantity,
                    weight=variant.get("weight"),
                ))

        # If no variants, create a default one
        if not variants:
            variants.append(Variant(
                id=str(data.get("id", "")),
                price_amount=price_amount,
                currency=currency,
                available=True,
            ))

        # Extract additional metadata
        brand = data.get("vendor")
        category = data.get("product_type")
        
        # Extract tags
        tags = []
        if data.get("tags"):
            tags = [tag.strip() for tag in data["tags"].split(",") if tag.strip()]
        
        # Extract weight from first variant
        weight = None
        if variants_list and variants_list[0].get("weight"):
            weight = variants_list[0]["weight"]

        # Extract meta information
        meta_title = title
        meta_description = None
        if description:
            # Strip HTML for meta description
            import re
            clean_desc = re.sub(r'<[^>]+>', ' ', description)
            meta_description = clean_desc[:400].strip() if clean_desc else None
        
        # Extract slug from handle
        slug = handle

        # Shopify products typically require shipping and track inventory
        requires_shipping = True
        track_quantity = True
        is_digital = False
        
        # Check if it's a digital product from tags or type
        if category and "digital" in category.lower():
            is_digital = True
            requires_shipping = False
        elif any("digital" in tag.lower() for tag in tags):
            is_digital = True
            requires_shipping = False

        return ProductResult(
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
            slug=slug,
            tags=tags,
            vendor=brand,  
            weight=weight,
            requires_shipping=requires_shipping,
            track_quantity=track_quantity,
            is_digital=is_digital,
            raw=payload,
        )


# ----------------------------- Amazon (RapidAPI: real-time-amazon-data) -----------------------------
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
        p = urlparse(url)
        host = (p.netloc or "").lower()

        # North & South America
        if host.endswith("amazon.com"):
            return "US"
        if host.endswith("amazon.ca"):
            return "CA"
        if host.endswith("amazon.com.mx"):
            return "MX"
        if host.endswith("amazon.com.br"):
            return "BR"

        # Europe
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

        # Asia & Middle East
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

        # Australia
        if host.endswith("amazon.com.au"):
            return "AU"

        # Default fallback
        return "US"

    def _extract_asin(self, url: str) -> t.Optional[str]:
        p = urlparse(url)
        m = _AMAZON_ASIN_RE.search(p.path)
        if m:
            return m.group(1)
        qs = parse_qs(p.query)
        if "asin" in qs and qs["asin"]:
            return qs["asin"][0]
        return None

    def fetch_product(self, url: str) -> ProductResult:
        if not self.cfg.rapidapi_key:
            raise ValueError("RapidAPI key not configured.")
        asin = self._extract_asin(url)
        if not asin:
            raise ValueError("ASIN not found in URL.")
        amazon_country = self._guess_country_from_url(url)

        host = "real-time-amazon-data.p.rapidapi.com"
        endpoint = "/product-details"
        params = {
            "asin": asin,
            "country":  amazon_country,
        }
        headers = {
            "X-RapidAPI-Key": self.cfg.rapidapi_key,
            "X-RapidAPI-Host": host,
        }

        r = self._http.get(f"https://{host}{endpoint}", headers=headers, params=params, timeout=self._http.request_timeout)
        r.raise_for_status()
        resp = r.json()
        data = resp.get("data") or {}

        # Extract basic product information
        title = data.get("product_title") or ""
        description = ""
        if data.get("about_product"):
            description = "<br>".join(data["about_product"])
        elif data.get("product_description"):
            description = data["product_description"]

        # Extract pricing
        price_amount = _parse_money_to_float(data.get("product_price"))
        currency = data.get("currency", "USD")
        price = {"amount": price_amount, "currency": currency}

        # Extract images - collect from multiple sources
        images = []
        if data.get("product_photo"):
            images.append(data["product_photo"])
        if data.get("product_photos"):
            images.extend(data["product_photos"])
        if data.get("aplus_images"):
            images.extend(data["aplus_images"])
        images = _dedupe(images)

        # Extract options and variants from product variations
        options = {}
        variants = []
        
        if data.get("product_variations_dimensions") and data.get("product_variations"):
            # Extract options from variations
            for dim in data["product_variations_dimensions"]:
                dim_name = dim.title()  # Normalize dimension name
                if dim in data["product_variations"]:
                    values = []
                    for var in data["product_variations"][dim]:
                        if var.get("is_available") and var.get("value"):
                            values.append(var["value"])
                    if values:
                        options[dim_name] = _dedupe(values)

            # Create variants from all_product_variations
            if data.get("all_product_variations"):
                for var_asin, var_options in data["all_product_variations"].items():
                    variant_options = {}
                    for dim, value in var_options.items():
                        dim_name = dim.title()
                        variant_options[dim_name] = value
                    
                    # Determine if this variant is available
                    is_available = data.get("product_availability", "").lower() == "in stock"
                    if var_asin != asin:
                        # For different ASINs, check if it's in the variations list
                        for dim in data.get("product_variations_dimensions", []):
                            if dim in data.get("product_variations", {}):
                                for var in data["product_variations"][dim]:
                                    if var.get("asin") == var_asin:
                                        is_available = var.get("is_available", False)
                                        break
                    
                    variants.append(Variant(
                        id=var_asin,
                        options=variant_options,
                        price_amount=price_amount,  # Use main product price for all variants
                        currency=currency,
                        available=is_available,
                    ))

        # If no variants found, create a default one
        if not variants:
            variants.append(Variant(
                id=asin,
                price_amount=price_amount,
                currency=currency,
                available=data.get("product_availability", "").lower() == "in stock",
            ))

        # Extract brand from product_details or product_information
        brand = None
        if data.get("product_details") and "Brand" in data["product_details"]:
            brand = data["product_details"]["Brand"]
        elif data.get("product_information") and "Manufacturer" in data["product_information"]:
            brand = data["product_information"]["Manufacturer"]
        
        # Extract brand from byline as fallback
        if not brand and data.get("product_byline"):
            byline = data["product_byline"]
            if byline.startswith("Visit the ") and byline.endswith(" Store"):
                brand = byline[10:-6]  # Extract brand name

        # Extract category from category_path (use most specific)
        category = None
        if data.get("category_path"):
            category = data["category_path"][-1].get("name")

        # Extract meta information
        meta_title = title
        meta_description = None
        if data.get("customers_say"):
            meta_description = data["customers_say"][:400]
        
        # Extract slug from product_slug
        slug = data.get("product_slug", "")

        # Extract tags from product information
        tags = []
        if data.get("product_information"):
            info = data["product_information"]
            if info.get("Special features"):
                tags.append(info["Special features"])
            if info.get("Compatible Devices"):
                tags.extend([device.strip() for device in info["Compatible Devices"].split(",")])
        
        # Extract vendor (seller information)
        vendor = brand  # Use brand as vendor for Amazon products

        # Extract weight from product_information
        weight = None
        if data.get("product_information") and "Item Weight" in data["product_information"]:
            weight_str = data["product_information"]["Item Weight"]
            try:
                # Extract numeric value from weight string like "0.01 ounces"
                import re
                weight_match = re.search(r"([\d.]+)", weight_str)
                if weight_match:
                    weight_val = float(weight_match.group(1))
                    # Convert ounces to grams if needed
                    if "ounce" in weight_str.lower():
                        weight = weight_val * 28.35  # Convert ounces to grams
                    else:
                        weight = weight_val
            except (ValueError, AttributeError):
                pass

        # Amazon products typically require shipping and are physical
        requires_shipping = True
        track_quantity = True
        is_digital = False

        return ProductResult(
            platform=self.platform,
            id=asin,
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
            tags=tags,
            vendor=vendor,
            weight=weight,
            requires_shipping=requires_shipping,
            track_quantity=track_quantity,
            is_digital=is_digital,
            raw=resp,
        )


# ----------------------------- Etsy (RapidAPI: etsy-api3 /details) -----------------------------
class EtsyRapidApiClient(ProductClient):
    platform = "etsy"

    def __init__(self, cfg: ApiConfig):
        self.cfg = cfg
        self._http = http_session()

    def _extract_listing_id(self, url: str) -> t.Optional[str]:
        p = urlparse(url)
        m = _ETSY_LISTING_RE.search(p.path)
        if m:
            return m.group(1)
        qs = parse_qs(p.query)
        if "listing_id" in qs and qs["listing_id"]:
            return qs["listing_id"][0]
        return None

    @staticmethod
    def _parse_variations(payload: dict) -> tuple[dict[str, list[str]], list[Variant]]:
        """
        Etsy variations can have multiple independent option types:
          [{"type": "Color / Size", "value": ["White / S ($23.97)", ...]},
           {"type": "Add-on Sleeve Print?", "value": ["Yes ($28.95)", "No ($23.97)"]}]
        
        We'll parse all option types and create a flattened options dict.
        For variants, we'll create combinations from the first major variant group.
        """
        options: dict[str, list[str]] = {}
        variants: list[Variant] = []

        var_blocks = payload.get("variations") or []
        if not isinstance(var_blocks, list) or not var_blocks:
            return options, variants

        def parse_price_from_paren(s: str) -> t.Optional[float]:
            # e.g. "White / S ($23.97 - $28.95)" -> extract min price
            m = re.search(r"\(([^\)]*)\)$", s)
            if not m:
                return None
            price_str = m.group(1)
            # Handle ranges like "$23.97 - $28.95" by taking the first price
            return _parse_money_to_float(price_str.split("-")[0] if "-" in price_str else price_str)

        # Process all variation blocks to extract options
        for block in var_blocks:
            if not isinstance(block, dict):
                continue
                
            type_str = block.get("type") or ""
            vals = block.get("value") or []
            
            if not vals:
                continue
            
            # Check if this is a compound type like "Color / Size"
            if "/" in type_str:
                dim_names = [s.strip() for s in type_str.split("/") if s.strip()]
                for dn in dim_names:
                    if dn not in options:
                        options[dn] = []
                
                # Parse compound values
                for entry in vals:
                    if not isinstance(entry, str):
                        continue
                    # Strip price part
                    clean = re.sub(r"\([^\)]*\)\s*$", "", entry).strip()
                    parts = [p.strip() for p in clean.split("/")]
                    
                    vopts: dict[str, str] = {}
                    for i, part in enumerate(parts):
                        if i < len(dim_names):
                            vopts[dim_names[i]] = part
                            if part not in options[dim_names[i]]:
                                options[dim_names[i]].append(part)
                    
                    vprice = parse_price_from_paren(entry)
                    
                    variants.append(Variant(
                        id=None,
                        sku=None,
                        title=" / ".join([f"{k}: {v}" for k, v in vopts.items()]) or None,
                        options=vopts,
                        price_amount=vprice,
                        currency=payload.get("currency"),
                        image=None,
                        available=None,
                        raw={"value": entry}
                    ))
            else:
                # Simple option type like "Add-on Sleeve Print?"
                opt_name = type_str.strip()
                if opt_name and opt_name not in options:
                    options[opt_name] = []
                
                for entry in vals:
                    if not isinstance(entry, str):
                        continue
                    clean = re.sub(r"\([^\)]*\)\s*$", "", entry).strip()
                    if clean and clean not in options[opt_name]:
                        options[opt_name].append(clean)

        return options, variants

    def fetch_product(self, url: str) -> ProductResult:
        if not self.cfg.rapidapi_key:
            raise ValueError("RapidAPI key not configured.")
        listing_id = self._extract_listing_id(url)
        if not listing_id:
            raise ValueError("Etsy listing_id not found in URL.")

        host = "etsy-api3.p.rapidapi.com"
        endpoint = "/details"
        params = {"url": url}
        headers = {
            "X-RapidAPI-Key": self.cfg.rapidapi_key,
            "X-RapidAPI-Host": host,
        }

        r = self._http.get(f"https://{host}{endpoint}", headers=headers, params=params, timeout=self._http.request_timeout)
        r.raise_for_status()
        resp = r.json()
        payload = resp.get("data") or {}

        # Extract basic product information
        title = payload.get("title") or ""
        description = ""
        if payload.get("item_details"):
            if isinstance(payload["item_details"], list):
                description = "<br>".join(payload["item_details"])
            else:
                description = str(payload["item_details"])
        elif payload.get("item_details_html"):
            description = payload["item_details_html"]

        # Extract pricing
        price_amount = payload.get("final_price") or payload.get("initial_price")
        currency = payload.get("currency", "USD")
        price = {"amount": price_amount, "currency": currency}

        # Extract images
        images = payload.get("images", [])
        images = _dedupe(images)

        # Extract options and variants using variations or product_specifications
        options = {}
        variants = []
        
        # Try variations first, then fallback to product_specifications
        if payload.get("variations"):
            options, variants = self._parse_variations(payload)
        elif payload.get("product_specifications"):
            # Parse from product_specifications format
            for spec in payload["product_specifications"]:
                spec_name = spec.get("specification_name", "")
                spec_values = spec.get("specification_values", "")
                
                if "/" in spec_name:  # Compound option like "Color / Size"
                    dim_names = [s.strip() for s in spec_name.split("/") if s.strip()]
                    for dn in dim_names:
                        if dn not in options:
                            options[dn] = []
                    
                    # Parse values like "White / S ($23.97 - $28.95); Black / M ($26.97 - $29.37)"
                    for entry in spec_values.split(";"):
                        entry = entry.strip()
                        if not entry:
                            continue
                        
                        # Extract price
                        price_match = re.search(r"\((\$[\d.,\-\s]+)\)", entry)
                        variant_price = price_amount
                        if price_match:
                            price_str = price_match.group(1).replace("$", "").split("-")[0].strip()
                            variant_price = _parse_money_to_float(price_str)
                        
                        # Remove price part and parse dimensions
                        clean = re.sub(r"\([^\)]*\)\s*$", "", entry).strip()
                        parts = [p.strip() for p in clean.split("/")]
                        
                        vopts = {}
                        for i, part in enumerate(parts):
                            if i < len(dim_names):
                                vopts[dim_names[i]] = part
                                if part not in options[dim_names[i]]:
                                    options[dim_names[i]].append(part)
                        
                        if vopts:
                            variants.append(Variant(
                                id=None,
                                sku=None,
                                title=" / ".join([f"{k}: {v}" for k, v in vopts.items()]),
                                options=vopts,
                                price_amount=variant_price,
                                currency=currency,
                                available=True,
                            ))
                else:
                    # Simple option
                    if spec_name not in options:
                        options[spec_name] = []
                    
                    for entry in spec_values.split(";"):
                        entry = entry.strip()
                        if entry:
                            clean = re.sub(r"\([^\)]*\)\s*$", "", entry).strip()
                            if clean and clean not in options[spec_name]:
                                options[spec_name].append(clean)

        # If no variants found, create a default one
        if not variants:
            variants.append(Variant(
                id=listing_id,
                price_amount=price_amount,
                currency=currency,
                available=True,
            ))

        # Extract additional metadata
        brand = payload.get("seller_shop_name") or payload.get("seller_name")
        
        # Extract category from breadcrumbs
        category = None
        if payload.get("breadcrumbs"):
            category = payload["breadcrumbs"][-1].get("name")
        elif payload.get("category_tree"):
            category = payload["category_tree"][-1] if payload["category_tree"] else None
        
        # Extract meta information
        meta_title = title
        meta_description = None
        if description and len(description) > 160:
            meta_description = description[:400]
        
        # Extract slug from URL or product_id
        slug = f"etsy-{listing_id}"
        
        # Extract tags from highlights
        tags = []
        if payload.get("highlights"):
            tags.extend(payload["highlights"])
        
        # Extract vendor information
        vendor = payload.get("seller_shop_name")
        
        # Extract material from description
        material = None
        if description:
            desc_lower = description.lower()
            if "cotton" in desc_lower:
                material = "Cotton"
            elif "polyester" in desc_lower:
                material = "Polyester"
            elif "wool" in desc_lower:
                material = "Wool"
            elif "silk" in desc_lower:
                material = "Silk"
        
        # Etsy products typically require shipping unless specified otherwise
        requires_shipping = True
        is_digital = False
        if description and "digital" in description.lower():
            is_digital = True
            requires_shipping = False

        return ProductResult(
            platform=self.platform,
            id=listing_id,
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
            tags=tags,
            vendor=vendor,
            requires_shipping=requires_shipping,
            track_quantity=True,
            is_digital=is_digital,
            raw=resp,
        )


# ----------------------------- AliExpress (RapidAPI: aliexpress-datahub /item_detail_6) -----------------------------
def _parse_aliexpress_result(resp: dict, item_id: str) -> ProductResult:
    result = resp.get("result", {}) if isinstance(resp, dict) else {}
    item = result.get("item", {}) if isinstance(result, dict) else {}

    # Extract basic product information
    title = item.get("title") or ""
    description = ""
    if item.get("description") and item["description"].get("html"):
        description = item["description"]["html"]

    # Extract pricing from SKU data
    sku_data = item.get("sku", {})
    sku_def = sku_data.get("def", {})

    price_amount = None
    currency = (
        result.get("settings", {}).get("currency")
        if isinstance(result.get("settings"), dict)
        else None
    ) or "USD"

    # Use promotion price if available, otherwise regular price
    if sku_def.get("promotionPrice") is not None:
        price_str = str(sku_def["promotionPrice"]).replace("$", "").split(" - ")[0]
        price_amount = _parse_money_to_float(price_str)
    elif sku_def.get("price") is not None:
        price_str = str(sku_def["price"]).replace("$", "").split(" - ")[0]
        price_amount = _parse_money_to_float(price_str)

    price = {"amount": price_amount, "currency": currency}

    def normalize_url(value: t.Any) -> t.Optional[str]:
        if not isinstance(value, str) or not value:
            return None
        if value.startswith("//"):
            return f"https:{value}"
        return value

    # Extract images and normalize URLs
    images: list[str] = []
    for raw_img in item.get("images", []) or []:
        normalized = normalize_url(raw_img)
        if normalized:
            images.append(normalized)
    images = _dedupe(images)

    # Extract options and variants from SKU data
    options: dict[str, list[str]] = {}
    variants: list[Variant] = []

    prop_lookup: dict[int, dict[str, t.Any]] = {}
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

        values_by_vid: dict[int, dict[str, t.Any]] = {}
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
        variant_image: t.Optional[str] = None

        # propMap format: "14:771;5:100014066"
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

        # Extract variant pricing
        variant_price = price_amount
        if sku.get("promotionPrice") is not None:
            variant_price = _parse_money_to_float(str(sku["promotionPrice"]).replace("$", ""))
        elif sku.get("price") is not None:
            variant_price = _parse_money_to_float(str(sku["price"]).replace("$", ""))

        # Extract availability/inventory
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

    # If no variants, create a default one
    if not variants and price_amount is not None:
        variants.append(
            Variant(
                id=str(item_id),
                price_amount=price_amount,
                currency=currency,
                available=item.get("available", True),
            )
        )

    # Extract additional metadata from properties
    properties = item.get("properties", {})
    prop_list = properties.get("list", []) if properties else []

    brand = None
    weight_grams: t.Optional[int] = None
    category = "Electronics"

    def parse_weight_to_grams(raw_value: t.Any) -> t.Optional[int]:
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

        # Heuristic for unit-less values from this API.
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

    # Extract vendor information
    vendor = None
    if result.get("seller") and result["seller"].get("storeTitle"):
        vendor = result["seller"]["storeTitle"]

    # Extract shipping/delivery package weight as fallback
    if weight_grams is None and result.get("delivery") and result["delivery"].get("packageDetail"):
        package = result["delivery"]["packageDetail"]
        weight_grams = parse_weight_to_grams(package.get("weight"))

    weight = float(weight_grams) if weight_grams is not None else None

    # AliExpress products are typically new and require shipping
    requires_shipping = True
    track_quantity = True
    is_digital = False

    # Extract slug
    slug = f"aliexpress-{item_id}"

    # Extract meta information
    meta_title = title
    meta_description = None
    if description and len(description) > 160:
        clean_desc = re.sub(r"<[^>]+>", " ", description)
        meta_description = clean_desc[:400].strip()

    return ProductResult(
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
        requires_shipping=requires_shipping,
        track_quantity=track_quantity,
        is_digital=is_digital,
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

        # 1️ Search for x_object_id 
        for values in query.values():
            for v in values:
                # Try raw
                m = _ALIEXPRESS_X_OBJECT_RE.search(v)
                if m:
                    return m.group(1)

                # Try decoded once (handles %3A, %253A, etc.)
                decoded = unquote(v)
                m = _ALIEXPRESS_X_OBJECT_RE.search(decoded)
                if m:
                    return m.group(1)

        # 2️ Fallback: item ID in path
        m = _ALIEXPRESS_ITEM_RE.search(parsed.path)
        if m:
            return m.group(1)

        return None

    def fetch_product(self, url: str) -> ProductResult:
        if not self.cfg.rapidapi_key:
            raise ValueError("RapidAPI key not configured for AliExpress.")
        item_id = self._extract_item_id(url)
        if not item_id:
            raise ValueError("AliExpress item_id not found in URL.")

        host = "aliexpress-datahub.p.rapidapi.com"
        endpoint = "/item_detail_6"
        params = {"itemId": item_id}
        headers = {
            "X-RapidAPI-Key": self.cfg.rapidapi_key,
            "X-RapidAPI-Host": host,
        }

        def _call(ep: str) -> dict:
            rr = self._http.get(f"https://{host}{ep}", headers=headers, params=params, timeout=self._http.request_timeout)
            rr.raise_for_status()
            return rr.json()

        resp = _call(endpoint)
        result = resp.get("result", {}) if isinstance(resp, dict) else {}
        item = result.get("item", {}) if isinstance(result, dict) else {}

        # If the primary endpoint didn't return useful item data, try the older
        # `item_detail_2` endpoint as a fallback and prefer its result when it
        # contains a title.
        if not item or not item.get("title"):
            try:
                fallback_resp = _call("/item_detail_2")
                fallback_result = fallback_resp.get("result", {}) if isinstance(fallback_resp, dict) else {}
                fallback_item = fallback_result.get("item", {}) if isinstance(fallback_result, dict) else {}
                if fallback_item and fallback_item.get("title"):
                    resp = fallback_resp
            except Exception:
                # Ignore fallback errors and proceed with original response
                pass

        return _parse_aliexpress_result(resp, item_id)


# ----------------------------- Factory + Facade -----------------------------
class ProductClientFactory:
    """
    Factory that wires clients. By default:
      - Shopify: public JSON
      - Amazon/Etsy/AliExpress: RapidAPI (hardcoded providers)
    """

    def __init__(self, cfg: ApiConfig):
        self.cfg = cfg
        self._clients: dict[str, ProductClient] = {
            "shopify": ShopifyClient(),
            "amazon": AmazonRapidApiClient(cfg),
            "etsy": EtsyRapidApiClient(cfg),
            "aliexpress": AliExpressClient(cfg),
        }

    def for_url(self, url: str) -> ProductClient:
        info = detect_product_url(url)
        platform = info.get("platform")
        if not platform:
            raise ValueError("Unrecognized platform for URL.")
        client = self._clients.get(platform)
        if not client:
            raise ValueError(f"No client for platform {platform}")
        return client


def fetch_product_details(url: str, cfg: ApiConfig) -> ProductResult:
    client = ProductClientFactory(cfg).for_url(url)
    return client.fetch_product(url)

def requires_rapidapi(url: str) -> bool:
    info = detect_product_url(url)
    return info.get("platform") in {"amazon", "etsy", "aliexpress"}

def import_product(url: str, cfg: ApiConfig, include_raw: bool = False) -> dict:
    product = fetch_product_details(url, cfg)
    return product.to_dict(include_raw=include_raw)
