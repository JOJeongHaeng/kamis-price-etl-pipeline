from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class PriceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_name: str
    variety_name: str
    product_cls_name: str
    grade_name: str
    unit: str
    unit_size: str
    price: int
    examined_date: date
    freshness_days: int
    freshness_status: str
    freshness_label: str


class PricePageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: tuple[PriceItemResponse, ...]
    page: int
    page_size: int
    total: int
    total_pages: int
