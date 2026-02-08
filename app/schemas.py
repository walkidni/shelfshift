from __future__ import annotations

from pydantic import BaseModel, Field


class ImportRequest(BaseModel):
    product_url: str = Field(..., min_length=8, examples=["https://example.com/products/demo"])
