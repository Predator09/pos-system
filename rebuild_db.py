#!/usr/bin/env python3
"""
Delete the local SQLite database and recreate an empty schema.
Default user: admin / admin

Run from the pos-system folder:
    python rebuild_db.py
"""

from __future__ import annotations

import gc
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.database.connection as connmod
from app.database.connection import DatabaseConnection
from app.database.migrations import DatabaseMigrations
from app.services import auth_service
from app.services.shop_context import database_path


def _unlink_with_retry(path: Path, attempts: int = 8, delay: float = 0.35) -> None:
    last_err: OSError | None = None
    for _ in range(attempts):
        try:
            path.unlink()
            print(f"Removed: {path}")
            return
        except OSError as e:
            last_err = e
            time.sleep(delay)
    raise PermissionError(
        f"Could not delete {path}. Close SmartStock (and any DB browser) using this file, then run again."
    ) from last_err


def _remove_sqlite_files(db_path: Path) -> None:
    for path in (
        db_path,
        Path(str(db_path) + "-wal"),
        Path(str(db_path) + "-shm"),
    ):
        if path.is_file():
            _unlink_with_retry(path)


def main() -> None:
    db_path = database_path()

    if connmod.db.connection is not None:
        connmod.db.close()
    gc.collect()

    if db_path.is_file():
        _remove_sqlite_files(db_path)
    else:
        print(f"No database file at {db_path} — will create a new one.")
        db_path.parent.mkdir(parents=True, exist_ok=True)

    dbc = DatabaseConnection()
    DatabaseMigrations(dbc).init_database()
    dbc.connect()

    connmod.db = dbc
    row = dbc.fetchone(
        "SELECT 1 FROM users WHERE lower(username) = lower(?)", ("admin",)
    )
    if row is None:
        pw = auth_service._hash_password("admin")
        dbc.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            ("admin", pw, "Administrator", "owner"),
        )

    dbc.close()
    connmod.db = DatabaseConnection()

    print("Done. Database rebuilt with all migrations.")
    print("Sign in with:  username  admin   password  admin")


if __name__ == "__main__":
    main()
