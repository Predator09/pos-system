"""Key/value app metadata (``db_version``) — does not alter other tables."""

from __future__ import annotations

from app.database.connection import db

_META_TABLE = "app_meta"
_VERSION_KEY = "db_version"
_DEFAULT_VERSION = 1


def _ensure_meta_table() -> None:
    db.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_META_TABLE} (
            key TEXT PRIMARY KEY NOT NULL,
            value TEXT NOT NULL
        )
        """
    )


def get_db_version() -> int:
    if db.connection is None:
        db.connect()
    _ensure_meta_table()
    row = db.fetchone(
        f"SELECT value FROM {_META_TABLE} WHERE key = ?",
        (_VERSION_KEY,),
    )
    if row is None:
        db.execute(
            f"INSERT OR IGNORE INTO {_META_TABLE} (key, value) VALUES (?, ?)",
            (_VERSION_KEY, str(_DEFAULT_VERSION)),
        )
        row = db.fetchone(
            f"SELECT value FROM {_META_TABLE} WHERE key = ?",
            (_VERSION_KEY,),
        )
        if row is None:
            return _DEFAULT_VERSION
    return int(row[0])


def set_db_version(version: int) -> None:
    if db.connection is None:
        db.connect()
    _ensure_meta_table()
    db.execute(
        f"""
        INSERT INTO {_META_TABLE} (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (_VERSION_KEY, str(int(version))),
    )
