from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from pdfminer.high_level import extract_text


DATE_PATTERN = re.compile(r"(20\d{2})[-./](\d{2})[-./](\d{2})")
PRICE_PATTERN = re.compile(r"\d{1,3}(?:,\d{3})*원")
PERCENT_PATTERN = re.compile(r"-?\d+(?:\.\d+)?%")
UNIT_PATTERN = re.compile(r"^(?:\d+(?:kg|g|개|포기|마리)|\d+kg|\d+g|\d+개|\d+포기|\d+마리|\d+\w+)$")
SEASON_FOOD_PATTERN = re.compile(r"꼭\s*먹어야\s*하는\s*['\"]?([^'\"\n]+)['\"]?")
SUMMARY_HINTS = ("가격이", "낮아졌", "올랐", "저렴", "비싸")
SUMMARY_STOP_MARKERS = ("주요 농축산물 소매가격", "가격비교 알뜰정보", "제철먹거리", "농축산물 수급정보")
ISSUE_START_MARKER = "농축산물 수급정보"
ISSUE_END_MARKERS = ("유통소비정책관",)
DATE_LINE_PATTERN = re.compile(r"^20\d{2}\.\d{2}\.\d{2}$")
NOISE_LINES = {"전국", "발행문의", "지난주", "이번주"}


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def extract_pdf_text(pdf_path: Path) -> str:
    text = extract_text(str(pdf_path))
    return text.replace("\xa0", " ")


def extract_report_date(text: str, fallback: date) -> date:
    match = DATE_PATTERN.search(text)
    if not match:
        return fallback
    year, month, day = map(int, match.groups())
    return date(year, month, day)


def derive_week_metadata(reference_date: date) -> dict[str, object]:
    iso_year, iso_week_no, iso_weekday = reference_date.isocalendar()
    start_date = reference_date - timedelta(days=iso_weekday - 1)
    end_date = start_date + timedelta(days=6)
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "week_no": iso_week_no,
        "year": iso_year,
        "month": reference_date.month,
    }


def _clean_lines(text: str) -> list[str]:
    return [line for line in (_normalize_line(line) for line in text.splitlines()) if line]


def _is_unit_line(line: str) -> bool:
    compact = line.replace(" ", "")
    return bool(UNIT_PATTERN.match(compact))


def _looks_like_food_name(line: str) -> bool:
    if line in NOISE_LINES:
        return False
    if PRICE_PATTERN.search(line) or PERCENT_PATTERN.search(line):
        return False
    if any(char.isdigit() for char in line):
        return False
    return len(line) >= 2


def extract_summary_headline(text: str) -> str | None:
    for line in _clean_lines(text):
        if DATE_PATTERN.search(line):
            continue
        if any(hint in line for hint in SUMMARY_HINTS):
            return line[:500]
    return None


def extract_summary_items(text: str, limit: int = 3) -> list[str]:
    lines = _clean_lines(text)
    try:
        start_idx = next(i for i, line in enumerate(lines) if any(hint in line for hint in SUMMARY_HINTS))
    except StopIteration:
        return []

    foods: list[str] = []
    idx = start_idx + 1
    while idx < len(lines):
        line = lines[idx]
        if any(marker in line for marker in SUMMARY_STOP_MARKERS):
            break
        if _looks_like_food_name(line):
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            if _is_unit_line(next_line):
                foods.append(line)
        if len(foods) >= limit:
            break
        idx += 1
    return foods


def extract_summary(text: str) -> str | None:
    headline = extract_summary_headline(text)
    items = extract_summary_items(text)
    if headline and items:
        return f"{headline} {' , '.join(items)}".replace(' , ', ', ')
    return headline


def extract_season_food(text: str) -> str | None:
    match = SEASON_FOOD_PATTERN.search(text)
    if not match:
        return None
    return _normalize_line(match.group(1))


def extract_issue(text: str) -> str | None:
    start_idx = text.rfind(ISSUE_START_MARKER)
    if start_idx < 0:
        return None

    issue_text = text[start_idx + len(ISSUE_START_MARKER):]
    end_positions = [issue_text.find(marker) for marker in ISSUE_END_MARKERS if issue_text.find(marker) >= 0]
    if end_positions:
        issue_text = issue_text[: min(end_positions)]

    cleaned_lines: list[str] = []
    for line in _clean_lines(issue_text):
        if DATE_LINE_PATTERN.match(line):
            continue
        if line in NOISE_LINES:
            continue
        if line == ISSUE_START_MARKER:
            continue
        if PRICE_PATTERN.search(line) and len(line) < 20:
            continue
        if PERCENT_PATTERN.search(line) and len(line) < 20:
            continue
        if _is_unit_line(line):
            continue
        if cleaned_lines and cleaned_lines[-1] == line:
            continue
        cleaned_lines.append(line)

    issue = "\n".join(cleaned_lines)
    return issue[:4000] if issue else None


def parse_weekly_report(pdf_path: Path) -> dict[str, object]:
    text = extract_pdf_text(pdf_path)
    fallback = date.fromtimestamp(pdf_path.stat().st_mtime)
    report_date = extract_report_date(text, fallback)
    metadata = derive_week_metadata(report_date)
    return {
        **metadata,
        "summary": extract_summary(text),
        "season_food": extract_season_food(text),
        "issue": extract_issue(text),
        "source_file": pdf_path.name,
        "report_date": report_date.isoformat(),
    }
