"""Generic key/value metadata in SQLite (``app_metadata`` table)."""

from __future__ import annotations

from typing import Optional

from app.database.connection import db

_TABLE = "app_metadata"
_SCHEMA_VERSION_KEY = "schema_version"
_LEGACY_DB_VERSION_KEY = "db_version"


def ensure_metadata_table() -> None:
    """Create ``app_metadata`` if it does not exist."""
    if db.connection is None:
        db.connect()
    db.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_TABLE} (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )


def get_metadata(key: str) -> Optional[str]:
    """Return stored value for *key*, or ``None`` if missing."""
    if db.connection is None:
        db.connect()
    ensure_metadata_table()
    row = db.fetchone(
        f"SELECT value FROM {_TABLE} WHERE key = ?",
        (key,),
    )
    if row is None:
        return None
    val = row[0]
    return None if val is None else str(val)


def set_metadata(key: str, value: str) -> None:
    """Upsert *key* → *value*."""
    if db.connection is None:
        db.connect()
    ensure_metadata_table()
    db.execute(
        f"""
        INSERT INTO {_TABLE} (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def get_schema_version() -> str:
    """
    Return semantic schema version from metadata, default ``0.0.0``.

    Backward compatibility: if legacy ``db_version`` exists and ``schema_version``
    is missing, copy legacy value into ``schema_version`` once.
    """
    v = get_metadata(_SCHEMA_VERSION_KEY)
    if v is None or not str(v).strip():
        legacy = get_metadata(_LEGACY_DB_VERSION_KEY)
        if legacy is not None and str(legacy).strip():
            v = str(legacy).strip()
            set_metadata(_SCHEMA_VERSION_KEY, v)
        else:
            return "0.0.0"
    return str(v).strip()


def set_schema_version(version: str) -> None:
    """Persist ``schema_version`` metadata."""
    set_metadata(_SCHEMA_VERSION_KEY, version)


def get_db_version() -> str:
    """Backward-compatible alias for schema version metadata."""
    return get_schema_version()


def set_db_version(version: str) -> None:
    """Backward-compatible alias for schema version metadata."""
    set_schema_version(version)
