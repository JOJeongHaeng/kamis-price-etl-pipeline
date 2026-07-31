from __future__ import annotations

import argparse
from pathlib import Path
from pprint import pprint

from etl.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the SmartShopping data pipeline")
    parser.add_argument("--raw-dir", type=Path, default=None, help="Optional external source directory containing ZIP, XLSX, and PDF files")
    parser.add_argument("--skip-pdfs", action="store_true", help="Skip PDF report parsing and process spreadsheets only")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    summary = run_pipeline(raw_dir=args.raw_dir, skip_pdfs=args.skip_pdfs)
    pprint(summary)
