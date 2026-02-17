import pytest

from typeshift.core.importers.csv.batch import import_products_from_csv


# ---------------------------------------------------------------------------
# Validation edge-case tests
# ---------------------------------------------------------------------------


def test_import_products_rejects_unsupported_platform() -> None:
    with pytest.raises(ValueError, match="source_platform must be one of"):
        import_products_from_csv(
            source_platform="magento",
            csv_bytes=b"col1,col2\na,b\n",
        )


def test_import_products_rejects_empty_csv() -> None:
    with pytest.raises(ValueError, match="CSV file is empty"):
        import_products_from_csv(
            source_platform="shopify",
            csv_bytes=b"",
        )


def test_import_products_rejects_oversized_csv() -> None:
    big = b"x" * (5 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="exceeds 5 MB"):
        import_products_from_csv(
            source_platform="shopify",
            csv_bytes=big,
        )


def test_import_products_requires_weight_unit_for_bigcommerce() -> None:
    csv_text = "Item,Name,Type,SKU,Price,Weight\nProduct,Test,physical,T1,10.00,\n"
    with pytest.raises(ValueError, match="source_weight_unit is required"):
        import_products_from_csv(
            source_platform="bigcommerce",
            csv_bytes=csv_text.encode(),
        )


def test_import_products_requires_weight_unit_for_wix() -> None:
    csv_text = "handle,fieldType,name,price,sku,inventory,media,weight\nalpha,PRODUCT,A,10,A1,1,,\n"
    with pytest.raises(ValueError, match="source_weight_unit is required"):
        import_products_from_csv(
            source_platform="wix",
            csv_bytes=csv_text.encode(),
        )


def test_import_products_requires_weight_unit_for_squarespace() -> None:
    csv_text = "Title,SKU,Price,Product Type [Non Editable],Visible,Product URL,Hosted Image URLs\nA,A1,10,PHYSICAL,No,,\n"
    with pytest.raises(ValueError, match="source_weight_unit is required"):
        import_products_from_csv(
            source_platform="squarespace",
            csv_bytes=csv_text.encode(),
        )


def test_import_products_rejects_invalid_weight_unit() -> None:
    csv_text = "Item,Name,Type,SKU,Price,Weight\nProduct,Test,physical,T1,10.00,\n"
    with pytest.raises(ValueError, match="source_weight_unit must be one of"):
        import_products_from_csv(
            source_platform="bigcommerce",
            csv_bytes=csv_text.encode(),
            source_weight_unit="stones",
        )


# ---------------------------------------------------------------------------
# Shopify batch tests
# ---------------------------------------------------------------------------


def test_import_products_from_csv_shopify_parses_multiple_products() -> None:
    csv_text = "\n".join(
        [
            "Handle,Title,Body (HTML),Variant SKU,Variant Price",
            "alpha,Alpha Product,Alpha description,ALPHA-1,10.00",
            "beta,Beta Product,Beta description,BETA-1,12.00",
        ]
    )

    products = import_products_from_csv(
        source_platform="shopify",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="",
    )

    assert len(products) == 2
    assert products[0].source.platform == "shopify"
    assert products[0].source.slug == "alpha"
    assert products[0].title == "Alpha Product"
    assert products[1].source.slug == "beta"
    assert products[1].title == "Beta Product"


def test_shopify_batch_multi_variant_product() -> None:
    csv_text = "\n".join(
        [
            "Handle,Title,Body (HTML),Variant SKU,Variant Price,Option1 Name,Option1 Value,Image Src,Variant Image,Variant Grams",
            "tshirt,V-Neck T-Shirt,Soft cotton,SQ-TEE-S,20.00,Size,S,https://cdn.example.com/img1.jpg,https://cdn.example.com/var_s.jpg,200",
            "tshirt,,,SQ-TEE-M,20.00,Size,M,,https://cdn.example.com/var_m.jpg,210",
            "mug,Coffee Mug,Ceramic mug,MUG-1,12.00,,,,,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="shopify",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 2

    tshirt = products[0]
    assert tshirt.title == "V-Neck T-Shirt"
    assert len(tshirt.variants) == 2
    assert tshirt.variants[0].sku == "SQ-TEE-S"
    assert tshirt.variants[1].sku == "SQ-TEE-M"
    assert tshirt.variants[0].option_values[0].name == "Size"
    assert tshirt.variants[0].option_values[0].value == "S"
    assert tshirt.variants[1].option_values[0].name == "Size"
    assert tshirt.variants[1].option_values[0].value == "M"
    assert len(tshirt.options) == 1
    assert tshirt.options[0].name == "Size"
    assert tshirt.options[0].values == ["S", "M"]

    mug = products[1]
    assert mug.title == "Coffee Mug"
    assert len(mug.variants) == 1
    assert mug.variants[0].sku == "MUG-1"


def test_shopify_batch_provenance() -> None:
    csv_text = "\n".join(
        [
            "Handle,Title,Body (HTML),Variant SKU,Variant Price",
            "alpha,Alpha,desc,A1,10",
            "beta,Beta,desc,B1,12",
            "gamma,Gamma,desc,G1,15",
        ]
    )

    products = import_products_from_csv(
        source_platform="shopify",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 3
    for product in products:
        prov = product.provenance["csv_import"]
        assert prov["detected_product_count"] == 3
        assert prov["selection_policy"] == "batch_all"
        assert prov["source_platform"] == "shopify"


# ---------------------------------------------------------------------------
# Wix batch tests
# ---------------------------------------------------------------------------


def test_import_products_from_csv_wix_parses_multiple_products() -> None:
    csv_text = "\n".join(
        [
            "handle,fieldType,name,price,sku,inventory,media,weight",
            "alpha,PRODUCT,Alpha Product,10.00,ALPHA-1,3,https://cdn.example.com/a.jpg,",
            "beta,PRODUCT,Beta Product,12.00,BETA-1,5,https://cdn.example.com/b.jpg,",
        ]
    )

    products = import_products_from_csv(
        source_platform="wix",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2
    assert products[0].source.platform == "wix"
    assert products[0].source.slug == "alpha"
    assert products[1].source.slug == "beta"


def test_wix_batch_multi_variant_product() -> None:
    csv_text = "\n".join(
        [
            "handle,fieldType,name,price,sku,inventory,media,weight,productOptionName1,productOptionType1,productOptionChoices1",
            "tshirt,PRODUCT,T-Shirt,29.99,TS-S,10,https://cdn.example.com/ts.jpg,,Size,TEXT_CHOICES,Small;Medium",
            "tshirt,VARIANT,,29.99,TS-S,10,,,Size,TEXT_CHOICES,Small",
            "tshirt,VARIANT,,29.99,TS-M,8,,,Size,TEXT_CHOICES,Medium",
            "mug,PRODUCT,Coffee Mug,12.00,MUG-1,20,https://cdn.example.com/mug.jpg,,,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="wix",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2

    tshirt = products[0]
    assert tshirt.title == "T-Shirt"
    assert len(tshirt.variants) == 2
    assert tshirt.variants[0].sku == "TS-S"
    assert tshirt.variants[1].sku == "TS-M"

    mug = products[1]
    assert mug.title == "Coffee Mug"
    assert len(mug.variants) == 1


def test_wix_batch_provenance() -> None:
    csv_text = "\n".join(
        [
            "handle,fieldType,name,price,sku,inventory,media,weight",
            "alpha,PRODUCT,Alpha,10,A1,1,,",
            "beta,PRODUCT,Beta,12,B1,2,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="wix",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2
    for product in products:
        prov = product.provenance["csv_import"]
        assert prov["detected_product_count"] == 2
        assert prov["selection_policy"] == "batch_all"


# ---------------------------------------------------------------------------
# Squarespace batch tests
# ---------------------------------------------------------------------------


def test_import_products_from_csv_squarespace_parses_multiple_products() -> None:
    csv_text = "\n".join(
        [
            "Title,SKU,Price,Product Type [Non Editable],Visible,Product URL,Hosted Image URLs",
            "Alpha Product,ALPHA-1,10.00,PHYSICAL,No,,",
            "Beta Product,BETA-1,12.00,PHYSICAL,No,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="squarespace",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2
    assert products[0].source.platform == "squarespace"
    assert products[0].title == "Alpha Product"
    assert products[1].title == "Beta Product"


def test_squarespace_batch_multi_variant_product() -> None:
    csv_text = "\n".join(
        [
            "Title,Description,SKU,Option Name 1,Option Value 1,Price,Sale Price,On Sale,Stock,Product Type [Non Editable],Visible,Product URL,Hosted Image URLs",
            "V-Neck Tee,Soft cotton,SQ-TEE-S,Size,S,20.00,,No,35,PHYSICAL,No,,",
            ",,SQ-TEE-M,Size,M,20.00,,No,25,PHYSICAL,,,",
            "Coffee Mug,Ceramic mug,MUG-1,,,12.00,,No,50,PHYSICAL,No,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="squarespace",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2

    tee = products[0]
    assert tee.title == "V-Neck Tee"
    assert len(tee.variants) == 2
    assert tee.variants[0].sku == "SQ-TEE-S"
    assert tee.variants[1].sku == "SQ-TEE-M"

    mug = products[1]
    assert mug.title == "Coffee Mug"
    assert len(mug.variants) == 1


def test_squarespace_batch_provenance() -> None:
    csv_text = "\n".join(
        [
            "Title,SKU,Price,Product Type [Non Editable],Visible,Product URL,Hosted Image URLs",
            "A,A1,10,PHYSICAL,No,,",
            "B,B1,12,PHYSICAL,No,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="squarespace",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="lb",
    )

    assert len(products) == 2
    for product in products:
        prov = product.provenance["csv_import"]
        assert prov["detected_product_count"] == 2
        assert prov["selection_policy"] == "batch_all"


# ---------------------------------------------------------------------------
# WooCommerce batch tests
# ---------------------------------------------------------------------------


def test_import_products_from_csv_woocommerce_parses_multiple_products() -> None:
    csv_text = "\n".join(
        [
            "Type,SKU,Name,Regular price,Images",
            "simple,WC-ALPHA,Alpha Product,10.00,",
            "simple,WC-BETA,Beta Product,12.00,",
        ]
    )

    products = import_products_from_csv(
        source_platform="woocommerce",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="",
    )

    assert len(products) == 2
    assert products[0].source.platform == "woocommerce"
    assert products[0].source.id == "WC-ALPHA"
    assert products[1].source.id == "WC-BETA"


def test_woocommerce_batch_variable_with_variations() -> None:
    csv_text = "\n".join(
        [
            "Type,SKU,Name,Regular price,Images,Parent,Attribute 1 name,Attribute 1 value(s)",
            "variable,VNECK-TSHIRT,V-Neck T-Shirt,,https://example.com/img1.jpg,,,",
            "variation,VNECK-TSHIRT-S,V-Neck T-Shirt - S,20.00,,VNECK-TSHIRT,Size,S",
            "variation,VNECK-TSHIRT-M,V-Neck T-Shirt - M,20.00,,VNECK-TSHIRT,Size,M",
            "simple,MUG-1,Coffee Mug,12.00,,,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="woocommerce",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 2

    tshirt = products[0]
    assert tshirt.title == "V-Neck T-Shirt"
    assert tshirt.source.id == "VNECK-TSHIRT"
    assert len(tshirt.variants) == 2
    assert tshirt.variants[0].sku == "VNECK-TSHIRT-S"
    assert tshirt.variants[1].sku == "VNECK-TSHIRT-M"
    assert tshirt.variants[0].option_values[0].name == "Size"
    assert tshirt.variants[0].option_values[0].value == "S"

    mug = products[1]
    assert mug.title == "Coffee Mug"
    assert len(mug.variants) == 1
    assert mug.variants[0].sku == "MUG-1"


def test_woocommerce_batch_multiple_variable_products() -> None:
    csv_text = "\n".join(
        [
            "Type,SKU,Name,Regular price,Images,Parent,Attribute 1 name,Attribute 1 value(s)",
            "variable,VNECK,V-Neck Tee,,,,Size,S;M",
            "variation,VNECK-S,,20,,VNECK,Size,S",
            "variation,VNECK-M,,20,,VNECK,Size,M",
            "variable,HOODIE,Hoodie,,,,Color,Red;Blue",
            "variation,HOODIE-R,,30,,HOODIE,Color,Red",
            "variation,HOODIE-B,,30,,HOODIE,Color,Blue",
        ]
    )

    products = import_products_from_csv(
        source_platform="woocommerce",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 2
    assert products[0].title == "V-Neck Tee"
    assert len(products[0].variants) == 2
    assert products[0].variants[0].sku == "VNECK-S"
    assert products[0].variants[1].sku == "VNECK-M"

    assert products[1].title == "Hoodie"
    assert len(products[1].variants) == 2
    assert products[1].variants[0].sku == "HOODIE-R"
    assert products[1].variants[1].sku == "HOODIE-B"


def test_woocommerce_batch_provenance() -> None:
    csv_text = "\n".join(
        [
            "Type,SKU,Name,Regular price,Images",
            "simple,A1,Alpha,10,",
            "simple,B1,Beta,12,",
        ]
    )

    products = import_products_from_csv(
        source_platform="woocommerce",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 2
    for product in products:
        prov = product.provenance["csv_import"]
        assert prov["detected_product_count"] == 2
        assert prov["selection_policy"] == "batch_all"


# ---------------------------------------------------------------------------
# BigCommerce batch tests
# ---------------------------------------------------------------------------


def test_import_products_from_csv_bigcommerce_modern_parses_multiple_products() -> None:
    csv_text = "\n".join(
        [
            "Item,Name,Type,SKU,Price,Weight",
            "Product,Alpha Product,physical,ALPHA-1,10.00,",
            "Product,Beta Product,physical,BETA-1,12.00,",
        ]
    )

    products = import_products_from_csv(
        source_platform="bigcommerce",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2
    assert products[0].source.platform == "bigcommerce"
    assert products[0].title == "Alpha Product"
    assert products[1].title == "Beta Product"


def test_import_products_from_csv_bigcommerce_legacy_parses_multiple_products() -> None:
    csv_text = "\n".join(
        [
            "Product Type,Code,Name,Calculated Price,Weight,Images",
            "P,ALPHA-1,Alpha Product,10.00,,",
            "P,BETA-1,Beta Product,12.00,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="bigcommerce",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2
    assert products[0].source.platform == "bigcommerce"
    assert products[0].title == "Alpha Product"
    assert products[1].title == "Beta Product"


def test_bigcommerce_modern_batch_with_variants_and_images() -> None:
    csv_text = "\n".join(
        [
            "Item,Name,Type,SKU,Price,Weight,Options,Variant Image URL,Image URL (Import),Image is Thumbnail,Image Sort Order",
            "Product,Guava Glow Set,physical,SH-101,29.99,,,,,,",
            "Variant,,,GG-SET-S,29.99,,Type=Rectangle|Name=Size|Value=Small,https://cdn.example.com/small.jpg,,,",
            "Variant,,,GG-SET-M,29.99,,Type=Rectangle|Name=Size|Value=Medium,https://cdn.example.com/medium.jpg,,,",
            "Image,,,,,,,,https://cdn.example.com/gallery1.jpg,TRUE,0",
            "Product,Lip Balm,physical,LB-1,9.99,,,,,,",
            "Image,,,,,,,,https://cdn.example.com/lip-balm.jpg,TRUE,0",
        ]
    )

    products = import_products_from_csv(
        source_platform="bigcommerce",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2

    guava = products[0]
    assert guava.title == "Guava Glow Set"
    assert len(guava.variants) == 2
    assert guava.variants[0].sku == "GG-SET-S"
    assert guava.variants[1].sku == "GG-SET-M"

    lip = products[1]
    assert lip.title == "Lip Balm"
    assert len(lip.variants) == 1
    assert lip.variants[0].sku == "LB-1"


def test_bigcommerce_batch_provenance_modern() -> None:
    csv_text = "\n".join(
        [
            "Item,Name,Type,SKU,Price,Weight",
            "Product,A,physical,A1,10,",
            "Product,B,physical,B1,12,",
            "Product,C,physical,C1,15,",
        ]
    )

    products = import_products_from_csv(
        source_platform="bigcommerce",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="g",
    )

    assert len(products) == 3
    for product in products:
        prov = product.provenance["csv_import"]
        assert prov["detected_product_count"] == 3
        assert prov["selection_policy"] == "batch_all"


def test_bigcommerce_batch_provenance_legacy() -> None:
    csv_text = "\n".join(
        [
            "Product Type,Code,Name,Calculated Price,Weight,Images",
            "P,A1,Alpha,10,,",
            "P,B1,Beta,12,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="bigcommerce",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="oz",
    )

    assert len(products) == 2
    for product in products:
        prov = product.provenance["csv_import"]
        assert prov["detected_product_count"] == 2
        assert prov["selection_policy"] == "batch_all"
