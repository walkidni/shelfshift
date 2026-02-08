from __future__ import annotations

from pydantic import BaseModel, Field


class ImportRequest(BaseModel):
    product_url: str = Field(..., min_length=8, examples=["https://example.com/products/demo"])


class ExportShopifyCsvRequest(BaseModel):
    product_url: str = Field(..., min_length=8, examples=["https://example.com/products/demo"])
    publish: bool = Field(default=False)


class ExportWooCommerceCsvRequest(BaseModel):
    product_url: str = Field(..., min_length=8, examples=["https://example.com/products/demo"])
    publish: bool = Field(default=False)
