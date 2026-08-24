from __future__ import annotations

import csv
from pathlib import Path

from config import API_OUTPUT_DIR, SCHEMA_PATH, ensure_directories
from db import engine as default_engine
from etl.api_extract import fetch_recent_kamis_prices
from etl.api_transform import RECENT_PRICE_SNAPSHOT_COLUMNS, create_kamis_dimensions, normalize_kamis_prices
from etl.load import ensure_schema, load_kamis_outputs


CATEGORY_COLUMNS = ["category_code", "category_name"]
PRODUCT_COLUMNS = ["item_code", "item_name", "category_code"]
PRODUCT_VARIANT_COLUMNS = ["item_code", "variety_code", "variety_name"]
GRADE_COLUMNS = ["grade_code", "grade_name"]


def write_csv(
    rows: list[dict[str, object]],
    columns: list[str],
    output_dir: Path,
    file_name: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_name
    with output_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def run_pipeline(engine=default_engine) -> dict[str, object]:
    ensure_directories()
    snapshot_rows = normalize_kamis_prices(fetch_recent_kamis_prices())
    dimensions = create_kamis_dimensions(snapshot_rows)

    ensure_schema(SCHEMA_PATH, engine=engine)
    output_specs = (
        ("recent_price_snapshot_csv", snapshot_rows, RECENT_PRICE_SNAPSHOT_COLUMNS, "recent_price_snapshot.csv"),
        ("category_csv", dimensions["category"], CATEGORY_COLUMNS, "category.csv"),
        ("product_csv", dimensions["product"], PRODUCT_COLUMNS, "product.csv"),
        ("product_variant_csv", dimensions["product_variant"], PRODUCT_VARIANT_COLUMNS, "product_variant.csv"),
        ("grade_csv", dimensions["grade"], GRADE_COLUMNS, "grade.csv"),
    )
    outputs = {
        key: str(write_csv(rows, columns, API_OUTPUT_DIR, file_name))
        for key, rows, columns, file_name in output_specs
    }
    load_summary = load_kamis_outputs(
        dimensions["category"],
        dimensions["product"],
        dimensions["product_variant"],
        dimensions["grade"],
        snapshot_rows,
        engine=engine,
    )

    return {
        "category_rows": len(dimensions["category"]),
        "product_rows": len(dimensions["product"]),
        "variant_rows": len(dimensions["product_variant"]),
        "grade_rows": len(dimensions["grade"]),
        "recent_price_snapshot_rows": len(snapshot_rows),
        "load_summary": load_summary,
        "outputs": outputs,
    }
