from __future__ import annotations

from sqlalchemy import Engine, text


def database_is_ready(engine: Engine) -> bool:
    """Return whether the price database can serve at least one snapshot."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1")).scalar_one()
        snapshot_count = connection.execute(
            text("SELECT COUNT(*) FROM RecentPriceSnapshot")
        ).scalar_one()
    return int(snapshot_count) >= 1
