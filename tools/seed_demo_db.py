from __future__ import annotations

from sqlalchemy import Engine, text

from web.database import create_web_engine


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS Category (
        category_code TEXT PRIMARY KEY,
        category_name TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Product (
        item_code TEXT PRIMARY KEY,
        item_name TEXT NOT NULL,
        category_code TEXT NOT NULL REFERENCES Category(category_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ProductVariant (
        variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT NOT NULL REFERENCES Product(item_code),
        variety_code TEXT NOT NULL,
        variety_name TEXT,
        UNIQUE(item_code, variety_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Grade (
        grade_code TEXT PRIMARY KEY,
        grade_name TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS RecentPriceSnapshot (
        snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
        variant_id INTEGER NOT NULL REFERENCES ProductVariant(variant_id),
        grade_code TEXT NOT NULL REFERENCES Grade(grade_code),
        examined_date DATE NOT NULL,
        product_cls_code TEXT NOT NULL,
        product_cls_name TEXT NOT NULL,
        unit TEXT NOT NULL,
        unit_size TEXT NOT NULL,
        price INTEGER NOT NULL,
        kg_price INTEGER,
        source_name TEXT NOT NULL,
        collected_at DATETIME NOT NULL,
        UNIQUE(variant_id, grade_code, examined_date, product_cls_code, unit, unit_size)
    )
    """,
)

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
        for statement in SCHEMA_STATEMENTS:
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
    count = seed_database(create_web_engine())
    print(f"Seeded {count} price snapshots.")
