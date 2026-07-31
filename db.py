from __future__ import annotations

from sqlalchemy import create_engine

from config import DB_DRIVER, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER, SQLITE_PATH, ensure_directories


def get_database_url() -> str:
    if DB_DRIVER == "mysql":
        return f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return f"sqlite:///{SQLITE_PATH.as_posix()}"


def get_engine(echo: bool = False):
    ensure_directories()
    return create_engine(get_database_url(), echo=echo)


engine = get_engine()
