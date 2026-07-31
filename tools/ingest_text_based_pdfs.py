from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from pprint import pprint

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd

from config import EXTRACTED_DATA_DIR, MART_OUTPUT_DIR, SCHEMA_PATH, ensure_directories
from db import engine
from etl.load import ensure_schema, load_pipeline_outputs
from etl.pdf_prices import parse_price_tables_from_pdf
from etl.report import parse_weekly_report
from etl.transform import build_analysis_mart, create_item_df, normalize_market_price, normalize_weekly_price

CLASSIFICATION_CSV = BASE_DIR / 'data' / 'processed' / 'marts' / 'pdf_source_classification.csv'


def load_text_based_pdf_paths(limit: int | None = None) -> list[Path]:
    rows = list(csv.DictReader(CLASSIFICATION_CSV.open(encoding='utf-8-sig')))
    selected = [
        EXTRACTED_DATA_DIR / row['archive'] / row['file_name']
        for row in rows
        if row['classification'] == 'text_based'
    ]
    selected = [path for path in selected if path.exists()]
    return selected[:limit] if limit is not None else selected


def apply_metadata(df: pd.DataFrame, metadata: dict[str, object]) -> pd.DataFrame:
    enriched = df.copy()
    for key, value in metadata.items():
        enriched[key] = value
    return enriched


def write_outputs(week_df: pd.DataFrame, weekly_report_df: pd.DataFrame, weekly_df: pd.DataFrame, market_df: pd.DataFrame, item_df: pd.DataFrame, analysis_df: pd.DataFrame) -> dict[str, str]:
    MART_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        'text_pdf_week_csv': MART_OUTPUT_DIR / 'text_pdf_week.csv',
        'text_pdf_weekly_report_csv': MART_OUTPUT_DIR / 'text_pdf_weekly_report.csv',
        'text_pdf_weekly_price_csv': MART_OUTPUT_DIR / 'text_pdf_weekly_price.csv',
        'text_pdf_market_price_csv': MART_OUTPUT_DIR / 'text_pdf_market_price.csv',
        'text_pdf_item_csv': MART_OUTPUT_DIR / 'text_pdf_item.csv',
        'text_pdf_analysis_csv': MART_OUTPUT_DIR / 'text_pdf_analysis_mart.csv',
    }
    week_df.to_csv(outputs['text_pdf_week_csv'], index=False, encoding='utf-8-sig')
    weekly_report_df.to_csv(outputs['text_pdf_weekly_report_csv'], index=False, encoding='utf-8-sig')
    weekly_df.to_csv(outputs['text_pdf_weekly_price_csv'], index=False, encoding='utf-8-sig')
    market_df.to_csv(outputs['text_pdf_market_price_csv'], index=False, encoding='utf-8-sig')
    item_df.to_csv(outputs['text_pdf_item_csv'], index=False, encoding='utf-8-sig')
    analysis_df.to_csv(outputs['text_pdf_analysis_csv'], index=False, encoding='utf-8-sig')
    return {key: str(value) for key, value in outputs.items()}


def ingest(limit: int | None = None) -> dict[str, object]:
    ensure_directories()
    pdf_paths = load_text_based_pdf_paths(limit=limit)

    weekly_frames: list[pd.DataFrame] = []
    market_frames: list[pd.DataFrame] = []
    week_records: list[dict[str, object]] = []
    weekly_report_records: list[dict[str, object]] = []
    skipped: list[str] = []

    for pdf_path in pdf_paths:
        try:
            report_data = parse_weekly_report(pdf_path)
            metadata = {key: report_data[key] for key in ('start_date', 'end_date', 'week_no', 'year', 'month')}
            week_records.append(metadata)
            weekly_report_records.append(report_data)

            weekly_pdf_df, market_pdf_df = parse_price_tables_from_pdf(pdf_path)
            if not weekly_pdf_df.empty:
                weekly_frames.append(apply_metadata(normalize_weekly_price(weekly_pdf_df, pdf_path), metadata))
            if not market_pdf_df.empty:
                market_frames.append(apply_metadata(normalize_market_price(market_pdf_df, pdf_path), metadata))
            if weekly_pdf_df.empty and market_pdf_df.empty:
                skipped.append(f'{pdf_path.name}: no_price_rows')
        except Exception as exc:
            skipped.append(f'{pdf_path.name}: {type(exc).__name__}')

    weekly_df = pd.concat(weekly_frames, ignore_index=True) if weekly_frames else pd.DataFrame(columns=['item_name', 'unit', 'last_price', 'current_price', 'change_rate', 'source_file', 'start_date', 'end_date', 'week_no', 'year', 'month'])
    market_df = pd.concat(market_frames, ignore_index=True) if market_frames else pd.DataFrame(columns=['item_name', 'unit', 'traditional_price', 'large_market_price', 'price_difference', 'source_file', 'start_date', 'end_date', 'week_no', 'year', 'month'])
    week_df = pd.DataFrame(week_records).drop_duplicates().sort_values(['year', 'week_no', 'start_date']).reset_index(drop=True) if week_records else pd.DataFrame(columns=['start_date', 'end_date', 'week_no', 'year', 'month'])
    weekly_report_df = pd.DataFrame(weekly_report_records).drop_duplicates(subset=['start_date', 'end_date', 'week_no', 'year', 'month']).reset_index(drop=True) if weekly_report_records else pd.DataFrame(columns=['start_date', 'end_date', 'week_no', 'year', 'month', 'summary', 'season_food', 'issue', 'source_file'])
    item_df = create_item_df(weekly_df, market_df)
    analysis_df = build_analysis_mart(weekly_df, market_df)

    ensure_schema(SCHEMA_PATH, engine=engine)
    load_summary = load_pipeline_outputs(item_df, week_df, weekly_report_df, weekly_df, market_df, engine=engine)
    outputs = write_outputs(week_df, weekly_report_df, weekly_df, market_df, item_df, analysis_df)

    return {
        'pdfs_selected': len(pdf_paths),
        'weekly_rows': len(weekly_df),
        'market_rows': len(market_df),
        'week_rows': len(week_df),
        'weekly_report_rows': len(weekly_report_df),
        'item_rows': len(item_df),
        'analysis_rows': len(analysis_df),
        'skipped_count': len(skipped),
        'skipped_preview': skipped[:20],
        'load_summary': load_summary,
        'outputs': outputs,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Ingest text-based PDFs only')
    parser.add_argument('--limit', type=int, default=None, help='Optional limit for the number of text-based PDFs to ingest')
    return parser


if __name__ == '__main__':
    args = build_parser().parse_args()
    pprint(ingest(limit=args.limit))
