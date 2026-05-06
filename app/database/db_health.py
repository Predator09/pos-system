"""Lightweight database health probe for startup (integrity + empty/reset detection)."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta

from app.database.connection import DatabaseConnection
from app.services.app_logging import get_logger


_EMPTY_RECENT_FILE_WINDOW_MINUTES = 15
_CRITICAL_EMPTY_TABLES = ("products", "sales")


def _db_file_recently_created(db: DatabaseConnection) -> bool:
    p = getattr(db, "db_path", None)
    if p is None:
        return False
    try:
        if not p.is_file():
            return False
        created = datetime.fromtimestamp(p.stat().st_ctime)
    except OSError:
        return False
    return datetime.now() - created <= timedelta(minutes=_EMPTY_RECENT_FILE_WINDOW_MINUTES)


def _critical_tables_empty(db: DatabaseConnection) -> bool:
    try:
        for table in _CRITICAL_EMPTY_TABLES:
            row = db.fetchone(f"SELECT COUNT(1) AS n FROM {table}")
            n = int(row[0]) if row else 0
            if n > 0:
                return False
        return True
    except (sqlite3.DatabaseError, TypeError, ValueError, IndexError):
        # If counts cannot be trusted, leave outcome to integrity/exception path.
        return False


def get_database_status(db: DatabaseConnection, *, db_preexisting: bool | None = None) -> str:
    """
    Return one of ``ok`` | ``missing`` | ``corrupted`` | ``empty``.

    - ``corrupted``: integrity check fails or DB operations error out.
    - ``missing``: DB file path does not exist, so startup should enter recovery/initialization handling.
    - ``empty``: critical business tables are empty OR DB file looks recently recreated.
    - ``ok``: healthy and populated (or brand-new first install).
    """
    db_path = getattr(db, "db_path", None)
    if db_path is not None and not os.path.exists(db_path):
        get_logger().warning("Database file is missing; recovery or initialization flow is required: %s", db_path)
        return "missing"

    if db.connection is None:
        db.connect()
    try:
        row = db.fetchone("PRAGMA integrity_check")
        if row is None or row[0] != "ok":
            return "corrupted"
        db.fetchone("SELECT 1 FROM sqlite_master LIMIT 1")

        # Avoid false positive on normal first install where migrations create a fresh empty DB.
        if db_preexisting is False:
            return "ok"

        if _critical_tables_empty(db) or _db_file_recently_created(db):
            return "empty"
        return "ok"
    except (sqlite3.DatabaseError, OSError, TypeError, IndexError):
        return "corrupted"


def probe_database_health(db: DatabaseConnection) -> str:
    """Backward-compatible alias for startup health checks."""
    return get_database_status(db)
