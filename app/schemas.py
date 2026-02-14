from typing import Literal
from pydantic import BaseModel, Field


class ImportRequest(BaseModel):
    product_url: str = Field(..., min_length=8, examples=["https://example.com/products/demo"])


class ExportShopifyCsvRequest(BaseModel):
    product_url: str = Field(..., min_length=8, examples=["https://example.com/products/demo"])
    publish: bool = Field(default=False)
    weight_unit: Literal["g", "kg", "lb", "oz"] = Field(default="g")


class ExportBigCommerceCsvRequest(BaseModel):
    product_url: str = Field(..., min_length=8, examples=["https://example.com/products/demo"])
    publish: bool = Field(default=False)
    csv_format: Literal["modern", "legacy"] = Field(default="modern")
    weight_unit: Literal["g", "kg", "lb", "oz"] = Field(default="kg")


class ExportWooCommerceCsvRequest(BaseModel):
    product_url: str = Field(..., min_length=8, examples=["https://example.com/products/demo"])
    publish: bool = Field(default=False)
    weight_unit: Literal["kg"] = Field(default="kg")


class ExportSquarespaceCsvRequest(BaseModel):
    product_url: str = Field(..., min_length=8, examples=["https://example.com/products/demo"])
    publish: bool = Field(default=False)
    product_page: str = Field(default="", examples=["shop"])
    squarespace_product_url: str = Field(default="", examples=["lemons"])
    weight_unit: Literal["kg", "lb"] = Field(default="kg")


class ExportWixCsvRequest(BaseModel):
    product_url: str = Field(..., min_length=8, examples=["https://example.com/products/demo"])
    publish: bool = Field(default=False)
    weight_unit: Literal["kg", "lb"] = Field(default="kg")
