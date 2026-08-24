from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import Engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.database import create_web_engine

SQLITE_SCHEMA_PATH = PROJECT_ROOT / "sql" / "sqlite_schema.sql"

CATEGORIES = (
    {"code": "100", "name": "식량작물"},
    {"code": "200", "name": "채소류"},
    {"code": "400", "name": "과일류"},
)

PRODUCTS = (
    {"code": "211", "name": "배추", "category": "200"},
    {"code": "212", "name": "양파", "category": "200"},
    {"code": "411", "name": "사과", "category": "400"},
)

VARIANTS = (
    {"id": 1, "item": "211", "code": "01", "name": "여름"},
    {"id": 2, "item": "212", "code": "01", "name": "양파"},
    {"id": 3, "item": "411", "code": "01", "name": "후지"},
)

SNAPSHOTS = (
    {"variant": 1, "date": "2026-08-21", "market_code": "01", "market": "소매", "unit": "포기", "size": "1", "price": 3450},
    {"variant": 1, "date": "2026-08-21", "market_code": "02", "market": "도매", "unit": "10kg", "size": "1", "price": 18600},
    {"variant": 2, "date": "2026-07-24", "market_code": "01", "market": "소매", "unit": "kg", "size": "1", "price": 2280},
    {"variant": 2, "date": "2026-07-24", "market_code": "02", "market": "도매", "unit": "15kg", "size": "1", "price": 17400},
    {"variant": 3, "date": "2025-08-23", "market_code": "01", "market": "소매", "unit": "개", "size": "1", "price": 2980},
    {"variant": 3, "date": "2025-08-22", "market_code": "02", "market": "도매", "unit": "10kg", "size": "1", "price": 46200},
)


def seed_database(engine: Engine) -> int:
    """Replace demo price data with a deterministic six-row fixture."""
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.execute(text("PRAGMA foreign_keys = ON"))
        schema = SQLITE_SCHEMA_PATH.read_text(encoding="utf-8")
        for statement in schema.split(";"):
            if statement.strip():
                connection.execute(text(statement))

        for table in ("RecentPriceSnapshot", "ProductVariant", "Product", "Category", "Grade"):
            connection.execute(text(f"DELETE FROM {table}"))

        connection.execute(
            text("INSERT INTO Category (category_code, category_name) VALUES (:code, :name)"),
            CATEGORIES,
        )
        connection.execute(
            text(
                "INSERT INTO Product (item_code, item_name, category_code) "
                "VALUES (:code, :name, :category)"
            ),
            PRODUCTS,
        )
        connection.execute(
            text(
                "INSERT INTO ProductVariant (variant_id, item_code, variety_code, variety_name) "
                "VALUES (:id, :item, :code, :name)"
            ),
            VARIANTS,
        )
        connection.execute(
            text("INSERT INTO Grade (grade_code, grade_name) VALUES ('04', '상품')")
        )
        connection.execute(
            text(
                "INSERT INTO RecentPriceSnapshot ("
                "variant_id, grade_code, examined_date, product_cls_code, "
                "product_cls_name, unit, unit_size, price, kg_price, source_name, collected_at"
                ") VALUES ("
                ":variant, '04', :date, :market_code, :market, :unit, :size, "
                ":price, NULL, 'PUBLIC_DATA_KAMIS', '2026-08-23 00:00:00'"
                ")"
            ),
            SNAPSHOTS,
        )

        return connection.execute(
            text("SELECT COUNT(*) FROM RecentPriceSnapshot")
        ).scalar_one()


if __name__ == "__main__":
    web_engine = create_web_engine()
    try:
        count = seed_database(web_engine)
    finally:
        web_engine.dispose()
    print(f"Seeded {count} price snapshots.")
