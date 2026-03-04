from shelfshift.core.importers.csv.detection import detect_csv_platform


def test_detect_csv_platform_shopify_legacy_headers() -> None:
    csv_text = "Handle,Title,Body (HTML),Variant SKU,Variant Price\nalpha,Alpha,Desc,A1,10.00\n"
    assert detect_csv_platform(csv_text.encode("utf-8")) == "shopify"


def test_detect_csv_platform_shopify_new_headers() -> None:
    csv_text = "Title,URL handle,Description,SKU,Price\nAlpha,alpha,Desc,A1,10.00\n"
    assert detect_csv_platform(csv_text.encode("utf-8")) == "shopify"
