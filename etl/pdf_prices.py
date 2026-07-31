from __future__ import annotations

from datetime import date
import re
from pathlib import Path

import pandas as pd

from etl.report import derive_week_metadata, extract_pdf_text

NUMBER_PATTERN = re.compile(r"^\d{1,3}(?:,\d{3})*$")
PERCENT_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?%$")
UNIT_PATTERN = re.compile(r"^(?:\d+(?:kg|g|개|포기|마리)|\d+kg|\d+g|\d+개|\d+포기|\d+마리|\d+L|\d+ml|\d+묶음|\d+봉)$")
DATE_RANGE_PATTERN = re.compile(r"\((\d{2})[./-](\d{2})\s*[~\-]\s*(\d{2})[./-](\d{2})\)")
FILE_FULL_DATE_RANGE_PATTERN = re.compile(r"(20\d{2})[._-](\d{2})[._-](\d{2})\s*[~\-]\s*(20\d{2})[._-](\d{2})[._-](\d{2})")
FILE_SHORT_END_DATE_RANGE_PATTERN = re.compile(r"(20\d{2})[._-](\d{2})[._-](\d{2})\s*[~\-]\s*(\d{2})[._-](\d{2})")
PAGE_NOISE = {"about:blank", "발행문의", "다운로드"}
WEEKLY_START = "주요 농축산물 소매가격"
MARKET_START = "가격비교 알뜰정보"
MARKET_END = "제철먹거리"


def _clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = " ".join(raw.replace("\xa0", " ").split()).strip()
        if not line:
            continue
        if line in PAGE_NOISE:
            continue
        if re.fullmatch(r"\d+/\d+", line):
            continue
        if re.fullmatch(r"\d{2}\. \d{2}\. \d{2}\. .+", line):
            continue
        lines.append(line)
    return lines


def _is_number(line: str) -> bool:
    return bool(NUMBER_PATTERN.match(line))


def _is_percent(line: str) -> bool:
    return bool(PERCENT_PATTERN.match(line))


def _is_unit(line: str) -> bool:
    compact = line.replace(" ", "")
    return bool(UNIT_PATTERN.match(compact))


def _find_indices(lines: list[str], marker: str) -> list[int]:
    return [idx for idx, line in enumerate(lines) if line == marker]


def _slice_weekly_section(lines: list[str]) -> list[str]:
    weekly_indices = _find_indices(lines, WEEKLY_START)
    market_indices = _find_indices(lines, MARKET_START)
    if not weekly_indices:
        return []
    start_idx = weekly_indices[1] + 1 if len(weekly_indices) >= 2 else weekly_indices[0] + 1
    end_idx = market_indices[-1] if market_indices else len(lines)
    return lines[start_idx:end_idx]


def _slice_market_section(lines: list[str]) -> list[str]:
    market_indices = _find_indices(lines, MARKET_START)
    end_indices = _find_indices(lines, MARKET_END)
    if not market_indices or not end_indices:
        return []
    start_idx = market_indices[-1] + 1
    end_idx = next((idx for idx in end_indices if idx > start_idx), len(lines))
    return lines[start_idx:end_idx]


def _infer_reference_year(source_file: Path) -> int:
    name = source_file.name

    match = FILE_FULL_DATE_RANGE_PATTERN.search(name)
    if match:
        return int(match.group(1))

    match = FILE_SHORT_END_DATE_RANGE_PATTERN.search(name)
    if match:
        return int(match.group(1))

    if source_file.exists():
        return date.fromtimestamp(source_file.stat().st_mtime).year

    return date.today().year


def extract_weekly_price_date_range(text: str, source_file: Path) -> tuple[str, str] | None:
    section = _slice_weekly_section(_clean_lines(text))
    if not section:
        return None

    matches = [DATE_RANGE_PATTERN.search(line) for line in section]
    parsed = [match.groups() for match in matches if match is not None]
    if not parsed:
        return None

    start_month, start_day, end_month, end_day = map(int, parsed[1] if len(parsed) >= 2 else parsed[0])
    year = _infer_reference_year(source_file)
    end_year = year + 1 if end_month < start_month else year

    start_date = date(year, start_month, start_day)
    end_date = date(end_year, end_month, end_day)
    return start_date.isoformat(), end_date.isoformat()


def _weekly_metadata(text: str, source_file: Path) -> dict[str, object] | None:
    date_range = extract_weekly_price_date_range(text, source_file)
    if date_range is None:
        return None
    start_date_text, end_date_text = date_range
    metadata = derive_week_metadata(date.fromisoformat(end_date_text))
    metadata["start_date"] = start_date_text
    metadata["end_date"] = end_date_text
    metadata["month"] = date.fromisoformat(end_date_text).month
    return metadata


def parse_weekly_price_from_text(text: str, source_file: Path) -> pd.DataFrame:
    metadata = _weekly_metadata(text, source_file)
    if metadata is None:
        return pd.DataFrame(columns=["item_name", "unit", "last_price", "current_price", "change_rate", "source_file", "start_date", "end_date", "week_no", "year", "month"])

    lines = _clean_lines(text)
    section = _slice_weekly_section(lines)
    records: list[dict[str, object]] = []

    i = 0
    while i + 4 < len(section):
        item_name = section[i]
        unit = section[i + 1]
        last_price = section[i + 2]
        current_price = section[i + 3]
        change_rate = section[i + 4]

        if (
            item_name not in {WEEKLY_START, "품목", "단위", "지난주", "이번주", "등락률", "등락률(%)", "(%)", "(단위 : 원, 상품)"}
            and _is_unit(unit)
            and _is_number(last_price)
            and _is_number(current_price)
            and _is_percent(change_rate)
        ):
            record = {
                "item_name": item_name,
                "unit": unit,
                "last_price": last_price,
                "current_price": current_price,
                "change_rate": change_rate,
                "source_file": source_file.name,
            }
            record.update(metadata)
            records.append(record)
            i += 5
            continue
        i += 1

    return pd.DataFrame.from_records(records)


def _extract_item_and_unit(lines: list[str], index: int) -> tuple[str, str, int] | None:
    line = lines[index]
    if " / " in line:
        item_name, unit = [part.strip() for part in line.split(" / ", 1)]
        if unit:
            return item_name, unit, index + 1
        if index + 1 < len(lines) and _is_unit(lines[index + 1]):
            return item_name, lines[index + 1], index + 2
    if line.endswith("/") and index + 1 < len(lines) and _is_unit(lines[index + 1]):
        return line[:-1].strip(), lines[index + 1], index + 2
    return None


def parse_market_price_from_text(text: str, source_file: Path) -> pd.DataFrame:
    lines = _clean_lines(text)
    section = _slice_market_section(lines)
    records: list[dict[str, object]] = []

    i = 0
    while i < len(section):
        parsed = _extract_item_and_unit(section, i)
        if parsed is None:
            i += 1
            continue

        item_name, unit, j = parsed
        prices: list[str] = []
        while j < len(section) and len(prices) < 2:
            token = section[j]
            if _is_number(token):
                prices.append(token)
            elif " / " in token or token.endswith("/"):
                break
            j += 1

        if len(prices) == 2:
            records.append(
                {
                    "item_name": item_name,
                    "unit": unit,
                    "traditional_price": prices[0],
                    "large_market_price": prices[1],
                    "price_difference": str(abs(int(prices[0].replace(',', '')) - int(prices[1].replace(',', '')))),
                    "source_file": source_file.name,
                }
            )
            i = j
            continue
        i += 1

    return pd.DataFrame.from_records(records)


def parse_price_tables_from_pdf(pdf_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    text = extract_pdf_text(pdf_path)
    weekly_df = parse_weekly_price_from_text(text, pdf_path)
    market_df = parse_market_price_from_text(text, pdf_path)
    return weekly_df, market_df
