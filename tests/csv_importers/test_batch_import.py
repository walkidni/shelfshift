import pytest

from shelfshift.core.importers.csv.batch import import_products_from_csv

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
    assert products[0].source.id is None
    assert products[0].source.slug == "alpha"
    assert products[0].title == "Alpha Product"
    assert products[1].source.id is None
    assert products[1].source.slug == "beta"
    assert products[1].title == "Beta Product"


def test_import_products_from_csv_shopify_new_template_parses_multiple_products() -> None:
    csv_text = "\n".join(
        [
            "Title,URL handle,Description,Vendor,Product category,Type,Tags,SKU,Option1 name,Option1 value,Price,Inventory quantity,Weight value (grams),Requires shipping,Product image URL,Variant image URL",
            'Alpha Product,alpha,Alpha description,Acme,Apparel & Accessories > Clothing > Shirts,Graphic shirt,"alpha,shirt",ALPHA-1,Size,S,10.00,3,200,TRUE,https://cdn.example.com/alpha.jpg,https://cdn.example.com/alpha-v.jpg',
            'Beta Product,beta,Beta description,Acme,Home & Garden > Kitchenware,Mug,"beta,mug",BETA-1,Size,One Size,12.00,5,250,TRUE,https://cdn.example.com/beta.jpg,https://cdn.example.com/beta-v.jpg',
        ]
    )

    products = import_products_from_csv(
        source_platform="shopify",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 2
    assert products[0].source.platform == "shopify"
    assert products[0].source.id is None
    assert products[0].source.slug == "alpha"
    assert products[0].title == "Alpha Product"
    assert products[0].variants[0].sku == "ALPHA-1"
    assert products[0].variants[0].inventory.quantity == 3
    assert str(products[0].variants[0].weight.value) == "200.0"
    assert products[0].taxonomy.primary == ["Apparel & Accessories", "Clothing", "Shirts"]
    assert products[0].unmapped_fields["shopify:type"] == "Graphic shirt"
    assert products[1].source.slug == "beta"
    assert products[1].source.id is None
    assert products[1].title == "Beta Product"
    assert products[1].variants[0].sku == "BETA-1"
    assert products[1].taxonomy.primary == ["Home & Garden", "Kitchenware"]
    assert products[1].unmapped_fields["shopify:type"] == "Mug"


def test_import_products_from_csv_shopify_does_not_infer_taxonomy_from_type() -> None:
    csv_text = "\n".join(
        [
            "Title,URL handle,Description,Vendor,Type,Tags,SKU,Price",
            'Alpha Product,alpha,Alpha description,Acme,Graphic shirt,"alpha,shirt",ALPHA-1,10.00',
        ]
    )

    products = import_products_from_csv(
        source_platform="shopify",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 1
    assert products[0].title == "Alpha Product"
    assert products[0].taxonomy.primary is None
    assert products[0].taxonomy.paths == []
    assert products[0].unmapped_fields["shopify:type"] == "Graphic shirt"


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


def test_shopify_batch_unknown_fields_are_ignored() -> None:
    csv_text = "\n".join(
        [
            "Handle,Title,Body (HTML),Variant SKU,Variant Price,Custom Product,Custom Variant",
            "alpha,Alpha,desc,A1,10,P-1,V-1",
        ]
    )

    products = import_products_from_csv(
        source_platform="shopify",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 1
    product = products[0]
    variant = product.variants[0]
    assert "shopify:custom_product" not in product.unmapped_fields
    assert "shopify:custom_variant" not in product.unmapped_fields
    assert "shopify:custom_product" not in variant.unmapped_fields
    assert "shopify:custom_variant" not in variant.unmapped_fields


def test_shopify_batch_maps_is_published_from_publish_only() -> None:
    csv_text = "\n".join(
        [
            "Title,URL handle,Description,SKU,Price,Published on online store,Status",
            "Alpha Product,alpha,Alpha description,ALPHA-1,10.00,TRUE,Active",
            "Beta Product,beta,Beta description,BETA-1,12.00,,Draft",
        ]
    )

    products = import_products_from_csv(
        source_platform="shopify",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 2
    assert products[0].is_published is True
    assert products[1].is_published is None


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
    assert products[0].source.id is None
    assert products[0].source.slug == "alpha"
    assert products[1].source.id is None
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


def test_wix_batch_maps_visibility() -> None:
    csv_text = "\n".join(
        [
            "handle,fieldType,name,visible,price,sku,inventory,media,weight",
            "alpha,PRODUCT,Alpha,TRUE,10,A1,1,,",
            "beta,PRODUCT,Beta,FALSE,12,B1,2,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="wix",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2
    assert products[0].is_published is True
    assert products[1].is_published is False


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
    assert products[0].source.id is None
    assert products[0].title == "Alpha Product"
    assert products[1].source.id is None
    assert products[1].title == "Beta Product"
    assert products[0].is_published is False
    assert products[1].is_published is False


def test_import_products_from_csv_squarespace_uses_explicit_id_headers() -> None:
    csv_text = "\n".join(
        [
            "Product ID [Non Editable],Variant ID [Non Editable],Title,SKU,Price,Product Type [Non Editable],Visible,Product URL,Hosted Image URLs",
            "P-101,V-101,Alpha Product,ALPHA-1,10.00,PHYSICAL,No,,",
            "P-102,V-201,Beta Product,BETA-1,12.00,PHYSICAL,No,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="squarespace",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2
    assert products[0].source.id == "P-101"
    assert products[0].variants[0].identifiers.values["source_variant_id"] == "V-101"
    assert products[1].source.id == "P-102"
    assert products[1].variants[0].identifiers.values["source_variant_id"] == "V-201"


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
            "ID,Type,SKU,Name,Regular price,Images",
            "101,simple,WC-ALPHA,Alpha Product,10.00,",
            "102,simple,WC-BETA,Beta Product,12.00,",
        ]
    )

    products = import_products_from_csv(
        source_platform="woocommerce",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="",
    )

    assert len(products) == 2
    assert products[0].source.platform == "woocommerce"
    assert products[0].source.id == "101"
    assert products[1].source.id == "102"


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
    assert tshirt.source.id is None
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


def test_woocommerce_batch_maps_visibility() -> None:
    csv_text = "\n".join(
        [
            "Type,SKU,Name,Regular price,Published,Visibility in catalog",
            "simple,A1,Alpha,10,1,visible",
            "simple,B1,Beta,12,0,visible",
            "simple,C1,Gamma,15,,hidden",
        ]
    )

    products = import_products_from_csv(
        source_platform="woocommerce",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 3
    assert products[0].is_published is True
    assert products[1].is_published is False
    assert products[2].is_published is None


def test_woocommerce_batch_uses_in_stock_header_as_boolean_source_of_truth() -> None:
    csv_text = "\n".join(
        [
            "Type,SKU,Name,Regular price,Stock,In stock?",
            "simple,A1,Alpha,10,7,0",
            "simple,B1,Beta,12,0,1",
        ]
    )

    products = import_products_from_csv(
        source_platform="woocommerce",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 2
    assert products[0].variants[0].inventory.quantity == 7
    assert products[0].variants[0].inventory.available is False
    assert products[1].variants[0].inventory.quantity == 0
    assert products[1].variants[0].inventory.available is True


@pytest.mark.parametrize(
    ("weight_header", "weight_value", "expected_grams"),
    [
        ("Weight (kg)", "1", 1000.0),
        ("Weight (lbs)", "1", 453.59237),
        ("Weight (g)", "1000", 1000.0),
        ("Weight (oz)", "16", 453.59237),
    ],
)
def test_woocommerce_batch_detects_weight_unit_from_weight_header(
    weight_header: str,
    weight_value: str,
    expected_grams: float,
) -> None:
    csv_text = "\n".join(
        [
            f"Type,SKU,Name,Regular price,{weight_header}",
            f"simple,A1,Alpha,10,{weight_value}",
        ]
    )

    products = import_products_from_csv(
        source_platform="woocommerce",
        csv_bytes=csv_text.encode("utf-8"),
    )

    assert len(products) == 1
    weight = products[0].variants[0].weight
    assert weight is not None
    assert float(weight.value) == pytest.approx(expected_grams, rel=1e-9, abs=1e-9)


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
    assert products[0].source.id is None
    assert products[0].title == "Alpha Product"
    assert products[1].source.id is None
    assert products[1].title == "Beta Product"


def test_import_products_from_csv_bigcommerce_modern_uses_explicit_id_header() -> None:
    csv_text = "\n".join(
        [
            "Item,ID,Name,Type,SKU,Price,Weight",
            "Product,1001,Alpha Product,physical,ALPHA-1,10.00,",
            "Product,1002,Beta Product,physical,BETA-1,12.00,",
        ]
    )

    products = import_products_from_csv(
        source_platform="bigcommerce",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2
    assert products[0].source.id == "1001"
    assert products[1].source.id == "1002"


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
    assert products[0].source.id is None
    assert products[0].title == "Alpha Product"
    assert products[1].source.id is None
    assert products[1].title == "Beta Product"


def test_import_products_from_csv_bigcommerce_legacy_uses_explicit_product_id_header() -> None:
    csv_text = "\n".join(
        [
            "Product ID,Product Type,Code,Name,Calculated Price,Weight,Images",
            "2001,P,ALPHA-1,Alpha Product,10.00,,",
            "2002,P,BETA-1,Beta Product,12.00,,",
        ]
    )

    products = import_products_from_csv(
        source_platform="bigcommerce",
        csv_bytes=csv_text.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(products) == 2
    assert products[0].source.id == "2001"
    assert products[1].source.id == "2002"


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


def test_bigcommerce_batch_maps_visibility() -> None:
    modern_csv = "\n".join(
        [
            "Item,Name,Type,SKU,Price,Weight,Is Visible",
            "Product,Alpha Product,physical,ALPHA-1,10.00,,TRUE",
            "Product,Beta Product,physical,BETA-1,12.00,,FALSE",
        ]
    )
    legacy_csv = "\n".join(
        [
            "Product Type,Code,Name,Calculated Price,Weight,Images,Product Visible",
            "P,LEG-A,Legacy Alpha,10.00,,,Y",
            "P,LEG-B,Legacy Beta,12.00,,,N",
        ]
    )

    modern_products = import_products_from_csv(
        source_platform="bigcommerce",
        csv_bytes=modern_csv.encode("utf-8"),
        source_weight_unit="kg",
    )
    legacy_products = import_products_from_csv(
        source_platform="bigcommerce",
        csv_bytes=legacy_csv.encode("utf-8"),
        source_weight_unit="kg",
    )

    assert len(modern_products) == 2
    assert modern_products[0].is_published is True
    assert modern_products[1].is_published is False
    assert len(legacy_products) == 2
    assert legacy_products[0].is_published is True
    assert legacy_products[1].is_published is False
