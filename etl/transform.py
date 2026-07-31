from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


WEEKLY_COLUMNS = ["item_name", "unit", "last_price", "current_price", "change_rate"]
MARKET_COLUMNS = ["item_name", "unit", "traditional_price", "large_market_price", "price_difference"]

INVALID_ITEM_EXACT = {"국산", "냉장", "냉동", "수입"}


def _normalize_numeric(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace({"": None, "nan": None, "-": None})
        .pipe(pd.to_numeric, errors="coerce")
    )


def _clean_text(value: object) -> str:
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    text = " ".join(text.split())
    while text.endswith("))"):
        text = text[:-1]
    return text


def _normalize_item_name(value: object) -> str:
    return _clean_text(value).strip(" -/")


def _normalize_unit(value: object) -> str:
    return _clean_text(value)


def _is_numeric_only(text: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:,\d{3})*", text))


def _is_percent_only(text: str) -> bool:
    return bool(re.fullmatch(r"-?\d+(?:\.\d+)?%", text))


def _is_paren_only(text: str) -> bool:
    return text.startswith("(") and text.endswith(")")


def _is_valid_item_name(value: object) -> bool:
    text = _normalize_item_name(value)
    bare = text.replace("(", "").replace(")", "").strip()

    if not text:
        return False
    if text in INVALID_ITEM_EXACT or bare in INVALID_ITEM_EXACT:
        return False
    if _is_numeric_only(text) or _is_percent_only(text) or _is_paren_only(text):
        return False
    if len(text) <= 1:
        return False
    if not any(ch.isalpha() for ch in text):
        return False

    return True


def _is_valid_unit(value: object) -> bool:
    text = _normalize_unit(value)

    if not text:
        return False
    if not re.search(r"\d", text):
        return False
    if _is_percent_only(text):
        return False
    if _is_paren_only(text):
        return False

    return True


def _filter_valid_item_rows(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()
    filtered["item_name"] = filtered["item_name"].map(_normalize_item_name)
    filtered["unit"] = filtered["unit"].map(_normalize_unit)
    mask = filtered["item_name"].map(_is_valid_item_name) & filtered["unit"].map(_is_valid_unit)
    return filtered.loc[mask].reset_index(drop=True)


def normalize_weekly_price(df: pd.DataFrame, source_file: Path) -> pd.DataFrame:
    weekly_df = df.iloc[:, :5].copy()
    weekly_df.columns = WEEKLY_COLUMNS
    weekly_df = weekly_df.dropna(how="all")
    weekly_df["item_name"] = weekly_df["item_name"].astype(str).str.strip()
    weekly_df["unit"] = weekly_df["unit"].astype(str).str.strip()
    weekly_df["last_price"] = _normalize_numeric(weekly_df["last_price"])
    weekly_df["current_price"] = _normalize_numeric(weekly_df["current_price"])
    weekly_df["change_rate"] = _normalize_numeric(weekly_df["change_rate"])
    weekly_df["source_file"] = source_file.name
    weekly_df = weekly_df.dropna(subset=["item_name", "unit", "last_price", "current_price", "change_rate"])
    weekly_df = _filter_valid_item_rows(weekly_df)
    return weekly_df.drop_duplicates(
        subset=["item_name", "unit", "last_price", "current_price", "change_rate", "source_file"]
    ).reset_index(drop=True)


def normalize_market_price(df: pd.DataFrame, source_file: Path) -> pd.DataFrame:
    market_df = df.iloc[:, :5].copy()
    market_df.columns = MARKET_COLUMNS
    market_df = market_df.dropna(how="all")
    market_df["item_name"] = market_df["item_name"].astype(str).str.strip()
    market_df["unit"] = market_df["unit"].astype(str).str.strip()
    for column in ["traditional_price", "large_market_price", "price_difference"]:
        market_df[column] = _normalize_numeric(market_df[column])
    market_df["source_file"] = source_file.name
    market_df = market_df.dropna(subset=["item_name", "unit", "traditional_price", "large_market_price"])
    market_df = _filter_valid_item_rows(market_df)
    return market_df.drop_duplicates(
        subset=["item_name", "unit", "traditional_price", "large_market_price", "price_difference", "source_file"]
    ).reset_index(drop=True)


def create_item_df(weekly_df: pd.DataFrame, market_df: pd.DataFrame) -> pd.DataFrame:
    item_df = (
        pd.concat(
            [
                weekly_df[["item_name", "unit"]].rename(columns={"item_name": "name"}),
                market_df[["item_name", "unit"]].rename(columns={"item_name": "name"}),
            ],
            ignore_index=True,
        )
        .drop_duplicates()
        .sort_values(["name", "unit"])
        .reset_index(drop=True)
    )
    return item_df


def build_analysis_mart(weekly_df: pd.DataFrame, market_df: pd.DataFrame) -> pd.DataFrame:
    weekly_view = weekly_df.assign(
        dataset_type="weekly",
        reference_price=weekly_df["current_price"],
        comparison_price=weekly_df["last_price"],
        price_gap=weekly_df["current_price"] - weekly_df["last_price"],
    )[
        [
            "item_name",
            "unit",
            "dataset_type",
            "reference_price",
            "comparison_price",
            "price_gap",
            "week_no",
            "year",
            "month",
            "source_file",
        ]
    ]

    market_view = market_df.assign(
        dataset_type="market",
        reference_price=market_df["large_market_price"],
        comparison_price=market_df["traditional_price"],
        price_gap=market_df["large_market_price"] - market_df["traditional_price"],
    )[
        [
            "item_name",
            "unit",
            "dataset_type",
            "reference_price",
            "comparison_price",
            "price_gap",
            "week_no",
            "year",
            "month",
            "source_file",
        ]
    ]

    return pd.concat([weekly_view, market_view], ignore_index=True)
