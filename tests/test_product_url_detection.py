from app.services.importer import requires_rapidapi
from app.services.product_url_detection import detect_product_url


def test_detect_shopify_product_url_shapes() -> None:
    canonical = detect_product_url("https://demo.myshopify.com/products/red-rain-coat")
    assert canonical["platform"] == "shopify"
    assert canonical["is_product"] is True
    assert canonical["slug"] == "red-rain-coat"

    collection_aware = detect_product_url(
        "https://demo.myshopify.com/collections/all/products/red-rain-coat"
    )
    assert collection_aware["platform"] == "shopify"
    assert collection_aware["is_product"] is True
    assert collection_aware["slug"] == "red-rain-coat"

    locale_prefixed = detect_product_url(
        "https://example-store.com/en-us/collections/sale/products/red-rain-coat"
    )
    assert locale_prefixed["platform"] == "shopify"
    assert locale_prefixed["is_product"] is True
    assert locale_prefixed["slug"] == "red-rain-coat"


def test_detect_shopify_js_and_json_urls_normalize_slug() -> None:
    js_endpoint = detect_product_url("https://demo.myshopify.com/products/red-rain-coat.js")
    assert js_endpoint["platform"] == "shopify"
    assert js_endpoint["is_product"] is True
    assert js_endpoint["slug"] == "red-rain-coat"

    json_endpoint = detect_product_url("https://demo.myshopify.com/products/red-rain-coat.json")
    assert json_endpoint["platform"] == "shopify"
    assert json_endpoint["is_product"] is True
    assert json_endpoint["slug"] == "red-rain-coat"


def test_detect_woocommerce_product_urls() -> None:
    query_form = detect_product_url("https://demo-store.com/?product=123")
    assert query_form["platform"] == "woocommerce"
    assert query_form["is_product"] is True
    assert query_form["product_id"] == "123"

    pretty_path = detect_product_url("https://demo-store.com/product/adjustable-wrench-set/")
    assert pretty_path["platform"] == "woocommerce"
    assert pretty_path["is_product"] is True
    assert pretty_path["slug"] == "adjustable-wrench-set"

    api_product_id = detect_product_url("https://demo-store.com/wp-json/wc/store/v1/products/123")
    assert api_product_id["platform"] == "woocommerce"
    assert api_product_id["is_product"] is True
    assert api_product_id["product_id"] == "123"

    api_product_slug = detect_product_url("https://demo-store.com/wp-json/wc/store/v1/products/brake-disc-rotor")
    assert api_product_slug["platform"] == "woocommerce"
    assert api_product_slug["is_product"] is True
    assert api_product_slug["slug"] == "brake-disc-rotor"


def test_detect_woocommerce_non_product_signal() -> None:
    api_url = detect_product_url("https://demo-store.com/wp-json/wc/store/v1/products")
    assert api_url["platform"] == "woocommerce"
    assert api_url["is_product"] is False
    assert api_url["product_id"] is None
    assert api_url["slug"] is None


def test_detect_squarespace_product_urls() -> None:
    with_p_segment = detect_product_url(
        "https://st-p-sews.squarespace.com/shop/p/custom-patchwork-shirt-snzgy"
    )
    assert with_p_segment["platform"] == "squarespace"
    assert with_p_segment["is_product"] is True
    assert with_p_segment["slug"] == "custom-patchwork-shirt-snzgy"

    store_path = detect_product_url("https://st-p-sews.squarespace.com/store/custom-patchwork-shirt-snzgy")
    assert store_path["platform"] == "squarespace"
    assert store_path["is_product"] is True
    assert store_path["slug"] == "custom-patchwork-shirt-snzgy"


def test_detect_squarespace_non_product_signal() -> None:
    home = detect_product_url("https://st-p-sews.squarespace.com/")
    assert home["platform"] == "squarespace"
    assert home["is_product"] is False
    assert home["slug"] is None


def test_detect_unknown_platform_returns_none() -> None:
    unknown = detect_product_url("https://example.com/anything")
    assert unknown["platform"] is None
    assert unknown["is_product"] is False
    assert unknown["product_id"] is None
    assert unknown["slug"] is None


def test_requires_rapidapi_only_for_amazon_and_aliexpress() -> None:
    assert requires_rapidapi("https://www.amazon.com/dp/B0C1234567") is True
    assert requires_rapidapi("https://www.aliexpress.com/item/1005008518647948.html") is True
    assert requires_rapidapi("https://demo.myshopify.com/products/red-rain-coat") is False
    assert requires_rapidapi("https://demo-store.com/product/adjustable-wrench-set/") is False
    assert requires_rapidapi("https://demo-store.com/wp-json/wc/store/v1/products/123") is False
    assert requires_rapidapi("https://st-p-sews.squarespace.com/shop/p/custom-patchwork-shirt-snzgy") is False
