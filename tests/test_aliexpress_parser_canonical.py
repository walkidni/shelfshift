from app.services.importer import _parse_aliexpress_result


def test_parse_aliexpress_result_uses_typed_weight_and_inventory_without_available() -> None:
    payload = {
        "result": {
            "settings": {"currency": "USD"},
            "delivery": {"packageDetail": {"weight": "1.100"}},
            "item": {
                "title": "Mask",
                "images": ["//ae01.alicdn.com/kf/base-image.png"],
                "description": {"html": "<div>desc</div>"},
                "sku": {
                    "def": {"promotionPrice": "50.40", "price": "120"},
                    "base": [
                        {
                            "skuId": "12000055918704599",
                            "propMap": "14:771",
                            "promotionPrice": "50.40",
                            "quantity": 200,
                        }
                    ],
                    "props": [
                        {
                            "pid": 14,
                            "name": "Color",
                            "values": [
                                {"vid": 771, "name": "Only Face mask", "image": "//ae01.alicdn.com/kf/face.png"},
                            ],
                        }
                    ],
                },
            },
        }
    }

    product = _parse_aliexpress_result(payload, "1005008518647948")
    parsed = product.to_dict(include_raw=False)

    assert parsed["weight"] == {"value": "1100", "unit": "g"}
    assert "available" not in parsed["variants"][0]
    assert parsed["variants"][0]["inventory"] == {
        "track_quantity": True,
        "quantity": 200,
        "available": True,
        "allow_backorder": None,
    }
