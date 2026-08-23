from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
EXTRACTED_DATA_DIR = DATA_DIR / "extracted"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
WEEKLY_OUTPUT_DIR = PROCESSED_DATA_DIR / "weekly_price"
MARKET_OUTPUT_DIR = PROCESSED_DATA_DIR / "market_price"
MART_OUTPUT_DIR = PROCESSED_DATA_DIR / "marts"
API_OUTPUT_DIR = PROCESSED_DATA_DIR / "api_price"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"
SOURCE_DATA_DIR = Path(os.getenv("SOURCE_DATA_DIR", str(RAW_DATA_DIR)))

KAMIS_API_URL = os.getenv("KAMIS_API_URL", "https://apis.data.go.kr/B552845/recent/price")
KAMIS_SERVICE_KEY = os.getenv("KAMIS_SERVICE_KEY", "")
KAMIS_API_TIMEOUT = float(os.getenv("KAMIS_API_TIMEOUT", "15"))
KAMIS_API_PAGE_SIZE = int(os.getenv("KAMIS_API_PAGE_SIZE", "1000"))

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "smartshopping")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_DRIVER = os.getenv("DB_DRIVER", "mysql")
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", str(BASE_DIR / "database" / "smartshopping.db")))


def ensure_directories() -> None:
    for path in (
        RAW_DATA_DIR,
        EXTRACTED_DATA_DIR,
        PROCESSED_DATA_DIR,
        WEEKLY_OUTPUT_DIR,
        MARKET_OUTPUT_DIR,
        MART_OUTPUT_DIR,
        API_OUTPUT_DIR,
        SQLITE_PATH.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
