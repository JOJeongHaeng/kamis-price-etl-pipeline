from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import pandas as pd

from config import API_OUTPUT_DIR, EXTRACTED_DATA_DIR, MART_OUTPUT_DIR, MARKET_OUTPUT_DIR, RAW_DATA_DIR, SCHEMA_PATH, SOURCE_DATA_DIR, WEEKLY_OUTPUT_DIR, ensure_directories
from db import engine as default_engine
from etl.api_extract import fetch_recent_kamis_prices
from etl.api_transform import RECENT_PRICE_SNAPSHOT_COLUMNS, create_kamis_dimensions, normalize_kamis_prices
from etl.extract import collect_report_files, collect_spreadsheet_files, load_excel_file
from etl.load import ensure_schema, load_kamis_outputs, load_pipeline_outputs
from etl.pdf_prices import parse_price_tables_from_pdf
from etl.report import derive_week_metadata, parse_weekly_report
from etl.transform import build_analysis_mart, create_item_df, normalize_market_price, normalize_weekly_price

FULL_DATE_RANGE_PATTERN = re.compile(r"(20\d{2})[._-](\d{2})[._-](\d{2})\s*[~\-]\s*(20\d{2})[._-](\d{2})[._-](\d{2})")
SHORT_END_DATE_RANGE_PATTERN = re.compile(r"(20\d{2})[._-](\d{2})[._-](\d{2})\s*[~\-]\s*(\d{2})[._-](\d{2})")
HEADER_DATE_RANGE_PATTERN = re.compile(r"(\d{2})[./](\d{2})\s*[~\-]\s*(\d{2})[./](\d{2})")


def infer_dataset_type(file_path: Path, df: pd.DataFrame) -> str | None:
    name = file_path.stem.lower()
    if any(keyword in name for keyword in ("weekly", "retail", "소매")):
        return "weekly"
    if any(keyword in name for keyword in ("market", "알뜰", "가격비교", "도매")):
        return "market"
    if df.shape[1] < 5:
        return None

    first_row = [str(value).lower() for value in df.iloc[0].tolist()]
    first_col = str(df.columns[0]).lower() if len(df.columns) else ""
    joined = " ".join(first_row + [first_col])

    if "(%)" in joined or "등락" in joined or "change" in joined:
        return "weekly"
    if any(token in joined for token in ("전통", "시장", "마트", "가격비", "traditional", "large")):
        return "market"
    return None


def _parse_date_range_from_name(file_path: Path) -> tuple[date, date] | None:
    name = file_path.name

    match = FULL_DATE_RANGE_PATTERN.search(name)
    if match:
        start_year, start_month, start_day, end_year, end_month, end_day = map(int, match.groups())
        try:
            return date(start_year, start_month, start_day), date(end_year, end_month, end_day)
        except ValueError:
            return None

    match = SHORT_END_DATE_RANGE_PATTERN.search(name)
    if match:
        start_year, start_month, start_day, end_month, end_day = map(int, match.groups())
        end_year = start_year + 1 if end_month < start_month else start_year
        try:
            return date(start_year, start_month, start_day), date(end_year, end_month, end_day)
        except ValueError:
            return None

    return None


def _parse_date_range_from_frame(df: pd.DataFrame, fallback_year: int) -> tuple[date, date] | None:
    values = []
    if len(df.columns):
        values.extend(str(col) for col in df.columns[:5])
    if len(df.index):
        values.extend(str(v) for v in df.iloc[0].tolist()[:5])
    joined = " ".join(values)
    match = HEADER_DATE_RANGE_PATTERN.search(joined)
    if not match:
        return None
    start_month, start_day, end_month, end_day = map(int, match.groups())
    end_year = fallback_year + 1 if end_month < start_month else fallback_year
    try:
        return date(fallback_year, start_month, start_day), date(end_year, end_month, end_day)
    except ValueError:
        return None


def infer_week_metadata(file_path: Path, df: pd.DataFrame | None = None) -> dict[str, object]:
    parsed = _parse_date_range_from_name(file_path)
    if parsed is not None:
        start_date, end_date = parsed
        metadata = derive_week_metadata(end_date)
        metadata["start_date"] = start_date.isoformat()
        metadata["end_date"] = end_date.isoformat()
        metadata["month"] = end_date.month
        return metadata

    reference_date = date.fromtimestamp(file_path.stat().st_mtime) if file_path.exists() else date(2026, 7, 29)
    if df is not None:
        parsed = _parse_date_range_from_frame(df, reference_date.year)
        if parsed is not None:
            start_date, end_date = parsed
            metadata = derive_week_metadata(end_date)
            metadata["start_date"] = start_date.isoformat()
            metadata["end_date"] = end_date.isoformat()
            metadata["month"] = end_date.month
            return metadata

    return derive_week_metadata(reference_date)


def apply_week_metadata(df: pd.DataFrame, metadata: dict[str, object]) -> pd.DataFrame:
    enriched = df.copy()
    for key, value in metadata.items():
        if key not in enriched.columns:
            enriched[key] = value
            continue
        enriched[key] = enriched[key].where(enriched[key].notna(), value)
    return enriched


def _write_csv(df: pd.DataFrame, output_dir: Path, file_name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_name
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def run_pipeline(
    raw_dir: Path | None = None,
    engine=default_engine,
    skip_pdfs: bool = False,
    include_api: bool = False,
    api_only: bool = False,
) -> dict[str, object]:
    ensure_directories()
    include_api = include_api or api_only
    source_dir = Path(raw_dir) if raw_dir is not None else SOURCE_DATA_DIR
    spreadsheets = [] if api_only else collect_spreadsheet_files(source_dir, EXTRACTED_DATA_DIR)
    report_files = [] if api_only or skip_pdfs else collect_report_files(source_dir, EXTRACTED_DATA_DIR)

    weekly_frames: list[pd.DataFrame] = []
    market_frames: list[pd.DataFrame] = []
    week_records: list[dict[str, object]] = []
    report_records: list[dict[str, object]] = []
    skipped_files: list[str] = []

    snapshot_df = (
        normalize_kamis_prices(fetch_recent_kamis_prices())
        if include_api
        else pd.DataFrame(columns=RECENT_PRICE_SNAPSHOT_COLUMNS)
    )

    for path in spreadsheets:
        try:
            frame = load_excel_file(path)
        except Exception as exc:
            skipped_files.append(f"{path.name}: read_error={type(exc).__name__}")
            continue

        dataset_type = infer_dataset_type(path, frame)
        metadata = infer_week_metadata(path, frame)
        week_records.append(metadata)
        try:
            if dataset_type == "weekly":
                weekly_frames.append(apply_week_metadata(normalize_weekly_price(frame, path), metadata))
            elif dataset_type == "market":
                market_frames.append(apply_week_metadata(normalize_market_price(frame, path), metadata))
            else:
                skipped_files.append(f"{path.name}: unsupported_layout")
        except Exception as exc:
            skipped_files.append(f"{path.name}: transform_error={type(exc).__name__}")

    for report_path in report_files:
        report_data = parse_weekly_report(report_path)
        metadata = {key: report_data[key] for key in ("start_date", "end_date", "week_no", "year", "month")}
        week_records.append(metadata)
        report_records.append(report_data)

        try:
            weekly_pdf_df, market_pdf_df = parse_price_tables_from_pdf(report_path)
            if not weekly_pdf_df.empty:
                weekly_frames.append(apply_week_metadata(weekly_pdf_df, metadata))
            if not market_pdf_df.empty:
                market_frames.append(apply_week_metadata(market_pdf_df, metadata))
        except Exception as exc:
            skipped_files.append(f"{report_path.name}: pdf_parse_error={type(exc).__name__}")

    weekly_df = pd.concat(weekly_frames, ignore_index=True) if weekly_frames else pd.DataFrame(columns=["item_name", "unit", "last_price", "current_price", "change_rate", "source_file", "start_date", "end_date", "week_no", "year", "month"])
    market_df = pd.concat(market_frames, ignore_index=True) if market_frames else pd.DataFrame(columns=["item_name", "unit", "traditional_price", "large_market_price", "price_difference", "source_file", "start_date", "end_date", "week_no", "year", "month"])
    week_df = pd.DataFrame(week_records).drop_duplicates().sort_values(["year", "week_no", "start_date"]).reset_index(drop=True) if week_records else pd.DataFrame(columns=["start_date", "end_date", "week_no", "year", "month"])
    weekly_report_df = pd.DataFrame(report_records).drop_duplicates(subset=["start_date", "end_date", "week_no", "year", "month"]).reset_index(drop=True) if report_records else pd.DataFrame(columns=["start_date", "end_date", "week_no", "year", "month", "summary", "season_food", "issue", "source_file"])
    item_df = create_item_df(weekly_df, market_df)
    analysis_mart_df = build_analysis_mart(weekly_df, market_df)

    ensure_schema(SCHEMA_PATH, engine=engine)
    outputs: dict[str, str] = {}
    load_summary: dict[str, int] = {}

    if not api_only:
        output_frames = (
            ("weekly_csv", weekly_df, WEEKLY_OUTPUT_DIR, "weekly_price.csv"),
            ("market_csv", market_df, MARKET_OUTPUT_DIR, "market_price.csv"),
            ("item_csv", item_df, MART_OUTPUT_DIR, "item.csv"),
            ("week_csv", week_df, MART_OUTPUT_DIR, "week.csv"),
            ("weekly_report_csv", weekly_report_df, MART_OUTPUT_DIR, "weekly_report.csv"),
            ("analysis_csv", analysis_mart_df, MART_OUTPUT_DIR, "price_analysis_mart.csv"),
        )
        outputs.update({key: str(_write_csv(frame, directory, name)) for key, frame, directory, name in output_frames})
        load_summary.update(load_pipeline_outputs(item_df, week_df, weekly_report_df, weekly_df, market_df, engine=engine))

    dimensions = create_kamis_dimensions(snapshot_df) if include_api else {
        "category": pd.DataFrame(columns=["category_code", "category_name"]),
        "product": pd.DataFrame(columns=["item_code", "item_name", "category_code"]),
        "product_variant": pd.DataFrame(columns=["item_code", "variety_code", "variety_name"]),
        "grade": pd.DataFrame(columns=["grade_code", "grade_name"]),
    }
    if include_api:
        api_frames = (
            ("recent_price_snapshot_csv", snapshot_df, "recent_price_snapshot.csv"),
            ("category_csv", dimensions["category"], "category.csv"),
            ("product_csv", dimensions["product"], "product.csv"),
            ("product_variant_csv", dimensions["product_variant"], "product_variant.csv"),
            ("grade_csv", dimensions["grade"], "grade.csv"),
        )
        outputs.update({key: str(_write_csv(frame, API_OUTPUT_DIR, name)) for key, frame, name in api_frames})
        load_summary.update(load_kamis_outputs(
            dimensions["category"], dimensions["product"], dimensions["product_variant"],
            dimensions["grade"], snapshot_df, engine=engine,
        ))

    return {
        "source_dir": str(source_dir),
        "spreadsheets_detected": len(spreadsheets),
        "reports_detected": len(report_files),
        "weekly_rows": len(weekly_df),
        "market_rows": len(market_df),
        "item_rows": len(item_df),
        "week_rows": len(week_df),
        "weekly_report_rows": len(weekly_report_df),
        "analysis_rows": len(analysis_mart_df),
        "category_rows": len(dimensions["category"]),
        "product_rows": len(dimensions["product"]),
        "variant_rows": len(dimensions["product_variant"]),
        "grade_rows": len(dimensions["grade"]),
        "recent_price_snapshot_rows": len(snapshot_df),
        "skipped_files": skipped_files,
        "load_summary": load_summary,
        "outputs": outputs,
    }
