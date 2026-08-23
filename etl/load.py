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
    daily_price_df: pd.DataFrame | None = None,
    engine=default_engine,
) -> dict[str, int]:
    if daily_price_df is None:
        daily_price_df = pd.DataFrame()

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

        daily_written = 0
        for row in daily_price_df.to_dict("records"):
            payload = {
                "product_no": row["product_no"],
                "price_date": row["price_date"],
                "product_cls_code": row["product_cls_code"],
                "product_cls_name": row["product_cls_name"],
                "category_code": _normalize_scalar(row.get("category_code")),
                "category_name": _normalize_scalar(row.get("category_name")),
                "variety_code": row["variety_code"],
                "variety_name": _normalize_scalar(row.get("variety_name")),
                "grade_code": row["grade_code"],
                "grade_name": _normalize_scalar(row.get("grade_name")),
                "unit": row["unit"],
                "unit_size": row["unit_size"],
                "price": int(row["price"]),
                "kg_price": _normalize_scalar(row.get("kg_price")),
                "day_before_price": _normalize_scalar(row.get("day_before_price")),
                "day_before_kg_price": _normalize_scalar(row.get("day_before_kg_price")),
                "week_before_price": _normalize_scalar(row.get("week_before_price")),
                "week_before_kg_price": _normalize_scalar(row.get("week_before_kg_price")),
                "month_before_price": _normalize_scalar(row.get("month_before_price")),
                "month_before_kg_price": _normalize_scalar(row.get("month_before_kg_price")),
                "year_before_price": _normalize_scalar(row.get("year_before_price")),
                "year_before_kg_price": _normalize_scalar(row.get("year_before_kg_price")),
                "source_name": row["source_name"],
                "collected_at": row["collected_at"],
                "item_id": item_id_map[(row["item_name"], row["unit"])],
            }
            existing = conn.execute(
                text(
                    """
                    SELECT daily_price_id
                    FROM DailyPrice
                    WHERE product_no = :product_no
                      AND price_date = :price_date
                      AND product_cls_code = :product_cls_code
                      AND variety_code = :variety_code
                      AND grade_code = :grade_code
                      AND unit = :unit
                      AND unit_size = :unit_size
                    """
                ),
                payload,
            ).scalar()
            if existing is None:
                conn.execute(
                    text(
                        """
                        INSERT INTO DailyPrice (
                            product_no, price_date, product_cls_code, product_cls_name,
                            category_code, category_name, variety_code, variety_name,
                            grade_code, grade_name, unit, unit_size, price, kg_price,
                            day_before_price, day_before_kg_price,
                            week_before_price, week_before_kg_price,
                            month_before_price, month_before_kg_price,
                            year_before_price, year_before_kg_price,
                            source_name, collected_at, item_id
                        ) VALUES (
                            :product_no, :price_date, :product_cls_code, :product_cls_name,
                            :category_code, :category_name, :variety_code, :variety_name,
                            :grade_code, :grade_name, :unit, :unit_size, :price, :kg_price,
                            :day_before_price, :day_before_kg_price,
                            :week_before_price, :week_before_kg_price,
                            :month_before_price, :month_before_kg_price,
                            :year_before_price, :year_before_kg_price,
                            :source_name, :collected_at, :item_id
                        )
                        """
                    ),
                    payload,
                )
            else:
                conn.execute(
                    text(
                        """
                        UPDATE DailyPrice
                        SET product_cls_name = :product_cls_name,
                            category_code = :category_code,
                            category_name = :category_name,
                            variety_name = :variety_name,
                            grade_name = :grade_name,
                            price = :price,
                            kg_price = :kg_price,
                            day_before_price = :day_before_price,
                            day_before_kg_price = :day_before_kg_price,
                            week_before_price = :week_before_price,
                            week_before_kg_price = :week_before_kg_price,
                            month_before_price = :month_before_price,
                            month_before_kg_price = :month_before_kg_price,
                            year_before_price = :year_before_price,
                            year_before_kg_price = :year_before_kg_price,
                            source_name = :source_name,
                            collected_at = :collected_at,
                            item_id = :item_id
                        WHERE product_no = :product_no
                          AND price_date = :price_date
                          AND product_cls_code = :product_cls_code
                          AND variety_code = :variety_code
                          AND grade_code = :grade_code
                          AND unit = :unit
                          AND unit_size = :unit_size
                        """
                    ),
                    payload,
                )
            daily_written += 1

    return {
        "items_upserted": len(item_id_map),
        "weeks_upserted": len(week_id_map),
        "weekly_reports_upserted": len(weekly_report_df),
        "weekly_prices_written": weekly_written,
        "market_prices_written": market_written,
        "daily_prices_written": daily_written,
    }
