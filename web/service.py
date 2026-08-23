from __future__ import annotations

from datetime import date

from web.models import PriceFilters, PriceItem, PricePage, classify_freshness
from web.repository import PriceRepository


class PriceService:
    def __init__(self, repository: PriceRepository):
        self.repository = repository

    def search(self, filters: PriceFilters, today: date | None = None) -> PricePage:
        rows, total = self.repository.search(filters)
        reference_date = today or date.today()
        items: list[PriceItem] = []

        for row in rows:
            examined_date = _as_date(row["examined_date"])
            freshness_days, freshness_status, freshness_label = classify_freshness(
                examined_date,
                reference_date,
            )
            items.append(
                PriceItem(
                    item_name=str(row["item_name"]),
                    variety_name=str(row["variety_name"]),
                    product_cls_name=str(row["product_cls_name"]),
                    grade_name=str(row["grade_name"]),
                    unit=str(row["unit"]),
                    unit_size=str(row["unit_size"]),
                    price=int(row["price"]),
                    examined_date=examined_date,
                    freshness_days=freshness_days,
                    freshness_status=freshness_status,
                    freshness_label=freshness_label,
                )
            )

        total_pages = (total + filters.page_size - 1) // filters.page_size if total else 0
        return PricePage(
            items=tuple(items),
            page=filters.page,
            page_size=filters.page_size,
            total=total,
            total_pages=total_pages,
        )


def _as_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
