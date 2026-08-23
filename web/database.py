from __future__ import annotations

from collections.abc import Mapping
import os

from sqlalchemy import Engine, create_engine

from config import SQLITE_PATH, ensure_directories


def resolve_database_url(environ: Mapping[str, str] | None = None) -> str:
    """Return the configured web database or the local SQLite demo database."""
    values = os.environ if environ is None else environ
    configured = values.get("DATABASE_URL", "").strip()
    return configured or f"sqlite:///{SQLITE_PATH.as_posix()}"


def create_web_engine(database_url: str | None = None) -> Engine:
    """Create a resilient SQLAlchemy engine for web queries."""
    ensure_directories()
    url = database_url or resolve_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite:") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)
