from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


DAILY_PRICE_COLUMNS = [
    "product_no", "item_name", "unit", "unit_size",
    "category_code", "category_name", "variety_code", "variety_name",
    "grade_code", "grade_name", "product_cls_code", "product_cls_name",
    "price_date", "price", "kg_price", "day_before_price",
    "day_before_kg_price", "week_before_price", "week_before_kg_price",
    "month_before_price", "month_before_kg_price", "year_before_price",
    "year_before_kg_price",
    "source_name", "collected_at",
]


def _price_rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    body = response.get("body", {})
    items = body.get("items", {}) if isinstance(body, dict) else {}
    rows = items.get("item", []) if isinstance(items, dict) else []
    if isinstance(rows, dict):
        rows = [rows]
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _normalize_price(value: Any) -> int | None:
    text = _clean_text(value).replace(",", "").replace("원", "")
    if not text or text in {"-", "null", "None"}:
        return None
    number = pd.to_numeric(text, errors="coerce")
    return None if pd.isna(number) else int(round(float(number)))


def _normalize_date(value: Any) -> str | None:
    parsed = pd.to_datetime(_clean_text(value), errors="coerce")
    return None if pd.isna(parsed) else parsed.date().isoformat()


def normalize_kamis_prices(
    response: dict[str, Any],
    *,
    collected_at: datetime | None = None,
) -> pd.DataFrame:
    """Convert the public-data recent price response into canonical rows."""
    collected = collected_at or datetime.now(timezone.utc)
    collected_text = collected.astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    records: list[dict[str, Any]] = []

    for row in _price_rows(response):
        record = {
            "product_no": _clean_text(row.get("item_cd")),
            "item_name": _clean_text(row.get("item_nm")),
            "unit": _clean_text(row.get("unit")),
            "unit_size": _clean_text(row.get("unit_sz")),
            "category_code": _clean_text(row.get("ctgry_cd")),
            "category_name": _clean_text(row.get("ctgry_nm")),
            "variety_code": _clean_text(row.get("vrty_cd")),
            "variety_name": _clean_text(row.get("vrty_nm")),
            "grade_code": _clean_text(row.get("grd_cd")),
            "grade_name": _clean_text(row.get("grd_nm")),
            "product_cls_code": _clean_text(row.get("se_cd")),
            "product_cls_name": _clean_text(row.get("se_nm")),
            "price_date": _normalize_date(row.get("exmn_ymd")),
            "price": _normalize_price(row.get("exmn_dd_prc")),
            "kg_price": _normalize_price(row.get("exmn_dd_cnvs_prc")),
            "day_before_price": _normalize_price(row.get("dd1_bfr_prc")),
            "day_before_kg_price": _normalize_price(row.get("dd1_bfr_cnvs_prc")),
            "week_before_price": _normalize_price(row.get("ww1_bfr_prc")),
            "week_before_kg_price": _normalize_price(row.get("ww1_bfr_cnvs_prc")),
            "month_before_price": _normalize_price(row.get("mm1_bfr_prc")),
            "month_before_kg_price": _normalize_price(row.get("mm1_bfr_cnvs_prc")),
            "year_before_price": _normalize_price(row.get("yy1_bfr_prc")),
            "year_before_kg_price": _normalize_price(row.get("yy1_bfr_cnvs_prc")),
            "source_name": "PUBLIC_DATA_KAMIS",
            "collected_at": collected_text,
        }
        required = ("product_no", "item_name", "unit", "product_cls_code", "price_date")
        if any(not record[key] for key in required) or record["price"] is None:
            continue
        records.append(record)

    if not records:
        return pd.DataFrame(columns=DAILY_PRICE_COLUMNS)

    unique_key = [
        "product_no", "variety_code", "grade_code", "price_date",
        "product_cls_code", "unit", "unit_size",
    ]
    return (
        pd.DataFrame.from_records(records, columns=DAILY_PRICE_COLUMNS)
        .drop_duplicates(subset=unique_key, keep="last")
        .sort_values(["price_date", "product_cls_code", "product_no", "variety_code", "grade_code"])
        .reset_index(drop=True)
    )
