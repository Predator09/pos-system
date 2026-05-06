"""App-level incremental migrations (separate from ``DatabaseMigrations`` in ``migrations.py``).

Uses ``app_meta`` / ``set_db_version`` from ``version_meta``. Add rows to ``MIGRATION_STEPS``;
each row is ``(target_version, [sql, ...])`` applied when ``current_version < target_version``.
"""

from __future__ import annotations

from app.database.connection import db
from app.database.version_meta import _ensure_meta_table, _META_TABLE, _VERSION_KEY
from app.services.app_logging import get_logger

# Ordered by ``target_version`` ascending. After each block succeeds, ``db_version`` is set to ``target_version``.
# Example:
# MIGRATION_STEPS: list[tuple[int, list[str]]] = [
#     (
#         2,
#         [
#             "CREATE TABLE IF NOT EXISTS example (id INTEGER PRIMARY KEY)",
#         ],
#     ),
# ]
MIGRATION_STEPS: list[tuple[int, list[str]]] = []


def run_migrations(current_version: int) -> int:
    """Apply pending SQL migrations. Returns the version after the last applied step (or ``current_version`` if none)."""
    if db.connection is None:
        db.connect()
    _ensure_meta_table()
    conn = db.connection

    v = int(current_version)
    for target, statements in MIGRATION_STEPS:
        if v >= target:
            continue
        conn.execute("BEGIN")
        try:
            for sql in statements:
                conn.execute(sql)
            conn.execute(
                f"""
                INSERT INTO {_META_TABLE} (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (_VERSION_KEY, str(int(target))),
            )
        except Exception:
            get_logger().exception("Migration to app db_version %s failed; rolling back.", target)
            conn.rollback()
            raise
        else:
            conn.commit()
        v = target
    return v
