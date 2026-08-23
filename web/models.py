from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


MarketType = Literal["retail", "wholesale"]


@dataclass(frozen=True)
class PriceFilters:
    query: str | None = None
    market_type: MarketType | None = None
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        normalized_query = self.query.strip() if self.query else None
        object.__setattr__(self, "query", normalized_query or None)
        if self.market_type not in (None, "retail", "wholesale"):
            raise ValueError("market_type must be retail or wholesale")
        if self.page < 1:
            raise ValueError("page must be at least 1")
        if not 1 <= self.page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")


@dataclass(frozen=True)
class PriceItem:
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


@dataclass(frozen=True)
class PricePage:
    items: tuple[PriceItem, ...]
    page: int
    page_size: int
    total: int
    total_pages: int


def classify_freshness(examined_date: date, today: date) -> tuple[int, str, str]:
    """Classify a price date with the same boundaries as KAMISPriceAnalysis."""
    days = max((today - examined_date).days, 0)
    if days <= 30:
        return days, "FRESH", "최신"
    try:
        one_year_ago = today.replace(year=today.year - 1)
    except ValueError:
        one_year_ago = today.replace(year=today.year - 1, day=28)
    if examined_date >= one_year_ago:
        return days, "CAUTION", "주의"
    return days, "STALE", "오래됨"
