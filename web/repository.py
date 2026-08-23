from __future__ import annotations

from sqlalchemy import Engine, text

from web.models import PriceFilters


MARKET_NAMES = {"retail": "소매", "wholesale": "도매"}

FROM_SQL = """
FROM RecentPriceSnapshot s
JOIN ProductVariant v ON v.variant_id = s.variant_id
JOIN Product p ON p.item_code = v.item_code
JOIN Grade g ON g.grade_code = s.grade_code
"""


class PriceRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def search(self, filters: PriceFilters) -> tuple[list[dict[str, object]], int]:
        conditions: list[str] = []
        parameters: dict[str, object] = {}

        if filters.query:
            conditions.append("LOWER(p.item_name) LIKE LOWER(:query)")
            parameters["query"] = f"%{filters.query}%"
        if filters.market_type:
            conditions.append("s.product_cls_name = :market_name")
            parameters["market_name"] = MARKET_NAMES[filters.market_type]

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        parameters.update(
            {
                "limit": filters.page_size,
                "offset": (filters.page - 1) * filters.page_size,
            }
        )
        select_sql = f"""
            SELECT
                p.item_name,
                COALESCE(v.variety_name, '') AS variety_name,
                s.product_cls_name,
                g.grade_name,
                s.unit,
                s.unit_size,
                s.price,
                s.examined_date
            {FROM_SQL}
            {where_sql}
            ORDER BY s.examined_date DESC, p.item_name ASC, s.snapshot_id ASC
            LIMIT :limit OFFSET :offset
        """
        count_sql = f"SELECT COUNT(*) {FROM_SQL} {where_sql}"

        with self.engine.connect() as connection:
            rows = connection.execute(text(select_sql), parameters).mappings().all()
            total = connection.execute(text(count_sql), parameters).scalar_one()

        return [dict(row) for row in rows], int(total)
