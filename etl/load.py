from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import text

from db import engine as default_engine


def _normalize_scalar(value: object) -> object | None:
    return None if value in (None, "") else value


def ensure_schema(schema_path: Path, engine=default_engine) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _upsert_by_code(conn, table: str, code_column: str, name_column: str, row: dict[str, object]) -> None:
    existing = conn.execute(
        text(f"SELECT {code_column} FROM {table} WHERE {code_column} = :code"),
        {"code": row[code_column]},
    ).scalar()
    payload = {"code": row[code_column], "name": row[name_column]}
    if existing is None:
        conn.execute(text(f"INSERT INTO {table} ({code_column}, {name_column}) VALUES (:code, :name)"), payload)
    else:
        conn.execute(text(f"UPDATE {table} SET {name_column} = :name WHERE {code_column} = :code"), payload)


def load_kamis_outputs(
    category_rows: list[dict[str, object]],
    product_rows: list[dict[str, object]],
    variant_rows: list[dict[str, object]],
    grade_rows: list[dict[str, object]],
    snapshot_rows: list[dict[str, object]],
    engine=default_engine,
) -> dict[str, int]:
    """Load normalized KAMIS dimensions and recent-price snapshots."""
    with engine.begin() as conn:
        for row in category_rows:
            _upsert_by_code(conn, "Category", "category_code", "category_name", row)

        for row in product_rows:
            payload = {key: row[key] for key in ("item_code", "item_name", "category_code")}
            existing = conn.execute(text("SELECT item_code FROM Product WHERE item_code = :item_code"), payload).scalar()
            if existing is None:
                conn.execute(text("INSERT INTO Product (item_code, item_name, category_code) VALUES (:item_code, :item_name, :category_code)"), payload)
            else:
                conn.execute(text("UPDATE Product SET item_name = :item_name, category_code = :category_code WHERE item_code = :item_code"), payload)

        variant_ids: dict[tuple[object, object], int] = {}
        for row in variant_rows:
            payload = {
                "item_code": row["item_code"],
                "variety_code": row["variety_code"],
                "variety_name": _normalize_scalar(row.get("variety_name")),
            }
            variant_id = conn.execute(text("SELECT variant_id FROM ProductVariant WHERE item_code = :item_code AND variety_code = :variety_code"), payload).scalar()
            if variant_id is None:
                conn.execute(text("INSERT INTO ProductVariant (item_code, variety_code, variety_name) VALUES (:item_code, :variety_code, :variety_name)"), payload)
                variant_id = conn.execute(text("SELECT variant_id FROM ProductVariant WHERE item_code = :item_code AND variety_code = :variety_code"), payload).scalar_one()
            else:
                conn.execute(text("UPDATE ProductVariant SET variety_name = :variety_name WHERE variant_id = :variant_id"), {**payload, "variant_id": variant_id})
            variant_ids[(row["item_code"], row["variety_code"])] = int(variant_id)

        for row in grade_rows:
            _upsert_by_code(conn, "Grade", "grade_code", "grade_name", row)

        snapshot_written = 0
        price_fields = (
            "kg_price", "day_before_price", "day_before_kg_price", "week_before_price",
            "week_before_kg_price", "month_before_price", "month_before_kg_price",
            "year_before_price", "year_before_kg_price",
        )
        for row in snapshot_rows:
            payload: dict[str, Any] = {
                "variant_id": variant_ids[(row["item_code"], row["variety_code"])],
                "grade_code": row["grade_code"], "examined_date": row["price_date"],
                "product_cls_code": row["product_cls_code"], "product_cls_name": row["product_cls_name"],
                "unit": row["unit"], "unit_size": row["unit_size"], "price": int(row["price"]),
                "source_name": row["source_name"], "collected_at": row["collected_at"],
                **{field: _normalize_scalar(row.get(field)) for field in price_fields},
            }
            where = "variant_id = :variant_id AND grade_code = :grade_code AND examined_date = :examined_date AND product_cls_code = :product_cls_code AND unit = :unit AND unit_size = :unit_size"
            existing = conn.execute(text(f"SELECT snapshot_id FROM RecentPriceSnapshot WHERE {where}"), payload).scalar()
            columns = (
                "variant_id", "grade_code", "examined_date", "product_cls_code", "product_cls_name",
                "unit", "unit_size", "price", *price_fields, "source_name", "collected_at",
            )
            if existing is None:
                conn.execute(text(f"INSERT INTO RecentPriceSnapshot ({', '.join(columns)}) VALUES ({', '.join(':' + column for column in columns)})"), payload)
            else:
                updated = ("product_cls_name", "price", *price_fields, "source_name", "collected_at")
                conn.execute(text(f"UPDATE RecentPriceSnapshot SET {', '.join(column + ' = :' + column for column in updated)} WHERE {where}"), payload)
            snapshot_written += 1

    return {
        "categories_upserted": len(category_rows), "products_upserted": len(product_rows),
        "variants_upserted": len(variant_rows), "grades_upserted": len(grade_rows),
        "snapshots_written": snapshot_written,
    }
