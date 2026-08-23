from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db import engine as default_engine


def _normalize_scalar(value):
    return None if pd.isna(value) else value


def ensure_schema(schema_path: Path, engine=default_engine) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _get_or_create_item_id(conn, name: str, unit: str) -> int:
    existing = conn.execute(
        text("SELECT item_id FROM Item WHERE name = :name AND unit = :unit"),
        {"name": name, "unit": unit},
    ).scalar()
    if existing is not None:
        return int(existing)

    conn.execute(
        text("INSERT INTO Item (name, unit) VALUES (:name, :unit)"),
        {"name": name, "unit": unit},
    )
    return int(
        conn.execute(
            text("SELECT item_id FROM Item WHERE name = :name AND unit = :unit"),
            {"name": name, "unit": unit},
        ).scalar_one()
    )


def _get_or_create_week_id(conn, week_row: dict[str, object]) -> int:
    existing = conn.execute(
        text(
            """
            SELECT week_id
            FROM Week
            WHERE start_date = :start_date
              AND end_date = :end_date
              AND week_no = :week_no
              AND year = :year
              AND month = :month
            """
        ),
        week_row,
    ).scalar()
    if existing is not None:
        return int(existing)

    conn.execute(
        text(
            """
            INSERT INTO Week (start_date, end_date, week_no, year, month)
            VALUES (:start_date, :end_date, :week_no, :year, :month)
            """
        ),
        week_row,
    )
    return int(
        conn.execute(
            text(
                """
                SELECT week_id
                FROM Week
                WHERE start_date = :start_date
                  AND end_date = :end_date
                  AND week_no = :week_no
                  AND year = :year
                  AND month = :month
                """
            ),
            week_row,
        ).scalar_one()
    )


def _upsert_weekly_report(conn, report_row: dict[str, object]) -> None:
    existing = conn.execute(
        text("SELECT report_id FROM WeeklyReport WHERE week_id = :week_id"),
        {"week_id": report_row["week_id"]},
    ).scalar()
    if existing is None:
        conn.execute(
            text(
                """
                INSERT INTO WeeklyReport (summary, season_food, week_id, issue)
                VALUES (:summary, :season_food, :week_id, :issue)
                """
            ),
            report_row,
        )
        return

    conn.execute(
        text(
            """
            UPDATE WeeklyReport
            SET summary = :summary,
                season_food = :season_food,
                issue = :issue
            WHERE week_id = :week_id
            """
        ),
        report_row,
    )


def load_pipeline_outputs(
    item_df: pd.DataFrame,
    week_df: pd.DataFrame,
    weekly_report_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    market_df: pd.DataFrame,
    engine=default_engine,
) -> dict[str, int]:
    with engine.begin() as conn:
        item_id_map: dict[tuple[str, str], int] = {}
        for row in item_df.to_dict("records"):
            item_id_map[(row["name"], row["unit"])] = _get_or_create_item_id(conn, row["name"], row["unit"])

        week_id_map: dict[tuple[str, str, int, int, int], int] = {}
        for row in week_df.to_dict("records"):
            week_key = (row["start_date"], row["end_date"], int(row["week_no"]), int(row["year"]), int(row["month"]))
            week_id_map[week_key] = _get_or_create_week_id(conn, row)

        for row in weekly_report_df.to_dict("records"):
            week_key = (row["start_date"], row["end_date"], int(row["week_no"]), int(row["year"]), int(row["month"]))
            report_row = {
                "summary": _normalize_scalar(row.get("summary")),
                "season_food": _normalize_scalar(row.get("season_food")),
                "issue": _normalize_scalar(row.get("issue")),
                "week_id": week_id_map[week_key],
            }
            _upsert_weekly_report(conn, report_row)

        weekly_written = 0
        for row in weekly_df.to_dict("records"):
            week_key = (row["start_date"], row["end_date"], int(row["week_no"]), int(row["year"]), int(row["month"]))
            payload = {
                "last_price": int(row["last_price"]),
                "current_price": int(row["current_price"]),
                "change_rate": float(row["change_rate"]),
                "item_id": item_id_map[(row["item_name"], row["unit"])],
                "week_id": week_id_map[week_key],
            }
            existing = conn.execute(
                text("SELECT price_id FROM WeeklyPrice WHERE item_id = :item_id AND week_id = :week_id"),
                payload,
            ).scalar()
            if existing is None:
                conn.execute(
                    text(
                        """
                        INSERT INTO WeeklyPrice (last_price, current_price, change_rate, item_id, week_id)
                        VALUES (:last_price, :current_price, :change_rate, :item_id, :week_id)
                        """
                    ),
                    payload,
                )
            else:
                conn.execute(
                    text(
                        """
                        UPDATE WeeklyPrice
                        SET last_price = :last_price,
                            current_price = :current_price,
                            change_rate = :change_rate
                        WHERE item_id = :item_id
                          AND week_id = :week_id
                        """
                    ),
                    payload,
                )
            weekly_written += 1

        market_written = 0
        for row in market_df.to_dict("records"):
            week_key = (row["start_date"], row["end_date"], int(row["week_no"]), int(row["year"]), int(row["month"]))
            payload = {
                "traditional_price": int(row["traditional_price"]),
                "largemarket_price": int(row["large_market_price"]),
                "item_id": item_id_map[(row["item_name"], row["unit"])],
                "week_id": week_id_map[week_key],
            }
            existing = conn.execute(
                text("SELECT MP_id FROM MarketPrice WHERE item_id = :item_id AND week_id = :week_id"),
                payload,
            ).scalar()
            if existing is None:
                conn.execute(
                    text(
                        """
                        INSERT INTO MarketPrice (traditional_price, largemarket_price, item_id, week_id)
                        VALUES (:traditional_price, :largemarket_price, :item_id, :week_id)
                        """
                    ),
                    payload,
                )
            else:
                conn.execute(
                    text(
                        """
                        UPDATE MarketPrice
                        SET traditional_price = :traditional_price,
                            largemarket_price = :largemarket_price
                        WHERE item_id = :item_id
                          AND week_id = :week_id
                        """
                    ),
                    payload,
                )
            market_written += 1

    return {
        "items_upserted": len(item_id_map),
        "weeks_upserted": len(week_id_map),
        "weekly_reports_upserted": len(weekly_report_df),
        "weekly_prices_written": weekly_written,
        "market_prices_written": market_written,
    }


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
    category_df: pd.DataFrame,
    product_df: pd.DataFrame,
    variant_df: pd.DataFrame,
    grade_df: pd.DataFrame,
    snapshot_df: pd.DataFrame,
    engine=default_engine,
) -> dict[str, int]:
    """Load normalized KAMIS dimensions and recent-price snapshots."""
    with engine.begin() as conn:
        for row in category_df.to_dict("records"):
            _upsert_by_code(conn, "Category", "category_code", "category_name", row)

        for row in product_df.to_dict("records"):
            payload = {key: row[key] for key in ("item_code", "item_name", "category_code")}
            existing = conn.execute(text("SELECT item_code FROM Product WHERE item_code = :item_code"), payload).scalar()
            if existing is None:
                conn.execute(text("INSERT INTO Product (item_code, item_name, category_code) VALUES (:item_code, :item_name, :category_code)"), payload)
            else:
                conn.execute(text("UPDATE Product SET item_name = :item_name, category_code = :category_code WHERE item_code = :item_code"), payload)

        variant_ids: dict[tuple[str, str], int] = {}
        for row in variant_df.to_dict("records"):
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

        for row in grade_df.to_dict("records"):
            _upsert_by_code(conn, "Grade", "grade_code", "grade_name", row)

        snapshot_written = 0
        price_fields = (
            "kg_price", "day_before_price", "day_before_kg_price", "week_before_price",
            "week_before_kg_price", "month_before_price", "month_before_kg_price",
            "year_before_price", "year_before_kg_price",
        )
        for row in snapshot_df.to_dict("records"):
            payload = {
                "variant_id": variant_ids[(row["item_code"], row["variety_code"])],
                "grade_code": row["grade_code"],
                "examined_date": row["price_date"],
                "product_cls_code": row["product_cls_code"],
                "product_cls_name": row["product_cls_name"],
                "unit": row["unit"], "unit_size": row["unit_size"],
                "price": int(row["price"]), "source_name": row["source_name"],
                "collected_at": row["collected_at"],
                **{field: _normalize_scalar(row.get(field)) for field in price_fields},
            }
            where = "variant_id = :variant_id AND grade_code = :grade_code AND examined_date = :examined_date AND product_cls_code = :product_cls_code AND unit = :unit AND unit_size = :unit_size"
            existing = conn.execute(text(f"SELECT snapshot_id FROM RecentPriceSnapshot WHERE {where}"), payload).scalar()
            columns = ("variant_id", "grade_code", "examined_date", "product_cls_code", "product_cls_name", "unit", "unit_size", "price", *price_fields, "source_name", "collected_at")
            if existing is None:
                conn.execute(text(f"INSERT INTO RecentPriceSnapshot ({', '.join(columns)}) VALUES ({', '.join(':' + column for column in columns)})"), payload)
            else:
                updated = ("product_cls_name", "price", *price_fields, "source_name", "collected_at")
                conn.execute(text(f"UPDATE RecentPriceSnapshot SET {', '.join(column + ' = :' + column for column in updated)} WHERE {where}"), payload)
            snapshot_written += 1

    return {
        "categories_upserted": len(category_df),
        "products_upserted": len(product_df),
        "variants_upserted": len(variant_df),
        "grades_upserted": len(grade_df),
        "snapshots_written": snapshot_written,
    }
