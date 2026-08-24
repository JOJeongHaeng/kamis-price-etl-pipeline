from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from typing import Any


RECENT_PRICE_SNAPSHOT_COLUMNS = [
    "item_code", "item_name", "unit", "unit_size",
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
    try:
        return int(Decimal(text).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
    except InvalidOperation:
        return None


def _normalize_date(value: Any) -> str | None:
    text = _clean_text(value)
    for date_format in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _snapshot_key(record: dict[str, object]) -> tuple[object, ...]:
    return tuple(record[column] for column in (
        "item_code", "variety_code", "grade_code", "price_date",
        "product_cls_code", "unit", "unit_size",
    ))


def _snapshot_sort_key(record: dict[str, object]) -> tuple[object, ...]:
    return tuple(record[column] for column in (
        "price_date", "product_cls_code", "item_code", "variety_code", "grade_code",
    ))


def normalize_kamis_prices(
    response: dict[str, Any],
    *,
    collected_at: datetime | None = None,
) -> list[dict[str, object]]:
    """Convert the public-data recent price response into canonical rows."""
    collected = collected_at or datetime.now(timezone.utc)
    collected_text = collected.astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    records_by_key: dict[tuple[object, ...], dict[str, object]] = {}

    for row in _price_rows(response):
        record = {
            "item_code": _clean_text(row.get("item_cd")),
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
        required = ("item_code", "item_name", "unit", "product_cls_code", "price_date")
        if any(not record[key] for key in required) or record["price"] is None:
            continue
        records_by_key[_snapshot_key(record)] = record

    return sorted(records_by_key.values(), key=_snapshot_sort_key)


def _unique_rows(
    snapshot_rows: list[dict[str, object]],
    identity_columns: tuple[str, ...],
    output_columns: tuple[str, ...],
) -> list[dict[str, object]]:
    rows_by_key: dict[tuple[object, ...], dict[str, object]] = {}
    for source_row in snapshot_rows:
        key = tuple(source_row[column] for column in identity_columns)
        rows_by_key[key] = {column: source_row[column] for column in output_columns}
    return [rows_by_key[key] for key in sorted(rows_by_key)]


def create_kamis_dimensions(
    snapshot_rows: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    """Build normalized KAMIS dimensions from canonical snapshot rows."""
    return {
        "category": _unique_rows(snapshot_rows, ("category_code",), ("category_code", "category_name")),
        "product": _unique_rows(snapshot_rows, ("item_code",), ("item_code", "item_name", "category_code")),
        "product_variant": _unique_rows(
            snapshot_rows,
            ("item_code", "variety_code"),
            ("item_code", "variety_code", "variety_name"),
        ),
        "grade": _unique_rows(snapshot_rows, ("grade_code",), ("grade_code", "grade_name")),
    }
