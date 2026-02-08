from app.services.importer import _parse_aliexpress_result


def test_parse_aliexpress_result_applies_currency_sku_category_and_weight() -> None:
    item_id = "1005008518647948"
    payload = {
        "result": {
            "settings": {"currency": "EUR"},
            "seller": {"storeTitle": "hello face Official Store"},
            "delivery": {"packageDetail": {"weight": "1.100"}},
            "item": {
                "available": True,
                "title": "LED Mask",
                "images": ["//ae01.alicdn.com/kf/base-image.png"],
                "description": {"html": '<div><img src="//ae01.alicdn.com/kf/detail-image.png"/></div>'},
                "properties": {
                    "list": [
                        {"name": "Brand Name", "value": "hello face"},
                        {"name": "Type", "value": "mask"},
                    ]
                },
                "sku": {
                    "def": {"promotionPrice": "50.40"},
                    "base": [
                        {
                            "skuId": "12000055918704599",
                            "propMap": "14:771",
                            "promotionPrice": "50.40",
                            "quantity": 200,
                        },
                        {
                            "skuId": "12000055918704598",
                            "propMap": "14:350853",
                            "promotionPrice": "60.40",
                            "quantity": 150,
                        },
                    ],
                    "props": [
                        {
                            "pid": 14,
                            "name": "Color",
                            "values": [
                                {"vid": 771, "name": "Only Face mask", "image": "//ae01.alicdn.com/kf/face.png"},
                                {"vid": 350853, "name": "Only Neck White", "image": "//ae01.alicdn.com/kf/neck.png"},
                            ],
                        }
                    ],
                    "skuImages": {
                        "14:771": "//ae01.alicdn.com/kf/face-sku.png",
                        "14:350853": "//ae01.alicdn.com/kf/neck-sku.png",
                    },
                },
            },
        }
    }

    product = _parse_aliexpress_result(payload, item_id)

    assert product.platform == "aliexpress"
    assert product.id == item_id
    assert product.price == {"amount": 50.4, "currency": "EUR"}
    assert product.category == "mask"
    assert product.vendor == "hello face Official Store"
    assert product.weight == 1100.0

    assert product.description == '<div><img src="//ae01.alicdn.com/kf/detail-image.png"/></div>'
    assert "//ae01.alicdn.com" in product.description

    assert product.options == {"Color": ["Only Face mask", "Only Neck White"]}
    assert len(product.variants) == 2
    assert product.variants[0].id == "12000055918704599"
    assert product.variants[0].sku == "AE:1005008518647948:12000055918704599"
    assert product.variants[0].currency == "EUR"
    assert product.variants[0].inventory_quantity == 200
    assert product.variants[0].options == {"Color": "Only Face mask"}
    assert product.variants[0].image == "https://ae01.alicdn.com/kf/face-sku.png"

    assert product.variants[1].id == "12000055918704598"
    assert product.variants[1].sku == "AE:1005008518647948:12000055918704598"
    assert product.variants[1].inventory_quantity == 150
    assert product.variants[1].options == {"Color": "Only Neck White"}
    assert product.variants[1].image == "https://ae01.alicdn.com/kf/neck-sku.png"

    # Item-level and variant-level images are merged and normalized.
    assert "https://ae01.alicdn.com/kf/base-image.png" in product.images
    assert "https://ae01.alicdn.com/kf/face-sku.png" in product.images
    assert "https://ae01.alicdn.com/kf/neck-sku.png" in product.images


def test_parse_aliexpress_result_falls_back_to_default_category() -> None:
    payload = {
        "result": {
            "settings": {"currency": "USD"},
            "item": {
                "title": "Simple Item",
                "images": [],
                "sku": {"def": {"promotionPrice": "10.00"}},
                "properties": {"list": [{"name": "Brand Name", "value": "Demo"}]},
            },
        }
    }

    product = _parse_aliexpress_result(payload, "10001")

    assert product.category == "Electronics"
