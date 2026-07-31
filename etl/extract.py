from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd


SPREADSHEET_SUFFIXES = {".xlsx", ".xls", ".xlsm"}
REPORT_SUFFIXES = {".pdf"}


def extract_zip_archives(raw_dir: Path, extracted_dir: Path) -> list[Path]:
    extracted_files: list[Path] = []
    for archive_path in sorted(raw_dir.glob("*.zip")):
        target_dir = extracted_dir / archive_path.stem
        target_dir.mkdir(parents=True, exist_ok=True)
        with ZipFile(archive_path) as archive:
            archive.extractall(target_dir)
        extracted_files.extend(path for path in target_dir.rglob("*") if path.is_file())
    return sorted(extracted_files)


def collect_files_by_suffix(raw_dir: Path, extracted_dir: Path, suffixes: set[str]) -> list[Path]:
    extract_zip_archives(raw_dir, extracted_dir)
    candidates = list(raw_dir.rglob("*")) + list(extracted_dir.rglob("*"))
    return sorted(
        path for path in candidates
        if path.is_file() and path.suffix.lower() in suffixes
    )


def collect_spreadsheet_files(raw_dir: Path, extracted_dir: Path) -> list[Path]:
    return collect_files_by_suffix(raw_dir, extracted_dir, SPREADSHEET_SUFFIXES)


def collect_report_files(raw_dir: Path, extracted_dir: Path) -> list[Path]:
    return collect_files_by_suffix(raw_dir, extracted_dir, REPORT_SUFFIXES)


def load_excel_file(filepath: Path) -> pd.DataFrame:
    suffix = filepath.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(filepath, engine="openpyxl")
    if suffix == ".xls":
        return pd.read_excel(filepath)
    return pd.read_excel(filepath)
