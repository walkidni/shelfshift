from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ImportRequest(BaseModel):
    product_urls: str | list[str] = Field(
        ...,
        examples=["https://example.com/products/demo"],
        description="One URL (string) or multiple URLs (list of strings) to import.",
    )

    @model_validator(mode="before")
    @classmethod
    def _compat_product_url(cls, data: Any) -> Any:
        """Accept legacy ``product_url`` (singular) as an alias."""
        if isinstance(data, dict) and "product_url" in data and "product_urls" not in data:
            data["product_urls"] = data.pop("product_url")
        return data

    @property
    def urls_list(self) -> list[str]:
        if isinstance(self.product_urls, str):
            return [self.product_urls]
        return list(self.product_urls)


class ExportShopifyCsvRequest(BaseModel):
    product: dict[str, Any]
    publish: bool = Field(default=False)
    weight_unit: Literal["g", "kg", "lb", "oz"] = Field(default="g")


class ExportBigCommerceCsvRequest(BaseModel):
    product: dict[str, Any]
    publish: bool = Field(default=False)
    csv_format: Literal["modern", "legacy"] = Field(default="modern")
    weight_unit: Literal["g", "kg", "lb", "oz"] = Field(default="kg")


class ExportWooCommerceCsvRequest(BaseModel):
    product: dict[str, Any]
    publish: bool = Field(default=False)
    weight_unit: Literal["kg"] = Field(default="kg")


class ExportSquarespaceCsvRequest(BaseModel):
    product: dict[str, Any]
    publish: bool = Field(default=False)
    product_page: str = Field(default="", examples=["shop"])
    squarespace_product_url: str = Field(default="", examples=["lemons"])
    weight_unit: Literal["kg", "lb"] = Field(default="kg")


class ExportWixCsvRequest(BaseModel):
    product: dict[str, Any]
    publish: bool = Field(default=False)
    weight_unit: Literal["kg", "lb"] = Field(default="kg")


class ExportFromProductCsvRequest(BaseModel):
    product: dict[str, Any] | list[dict[str, Any]]
    target_platform: Literal["shopify", "bigcommerce", "wix", "squarespace", "woocommerce"]
    publish: bool = Field(default=False)
    weight_unit: str = Field(default="")
    bigcommerce_csv_format: Literal["modern", "legacy"] = Field(default="modern")
    squarespace_product_page: str = Field(default="", examples=["shop"])
    squarespace_product_url: str = Field(default="", examples=["lemons"])
