"""Versioned JSON export of key tables (read-only SELECTs)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def backup_to_json(db_connection, output_path) -> Path:
    """Export ``products``, ``sales``, ``sale_items``, ``inventory_movements`` to ``output_path``.

    ``inventory_movements`` is omitted if the table does not exist (empty list in ``data``).
    """
    def _rows(table: str) -> list[dict]:
        try:
            return [dict(r) for r in db_connection.fetchall(f"SELECT * FROM {table}")]
        except sqlite3.OperationalError as exc:
            if table == "inventory_movements" and "no such table" in str(exc).lower():
                return []
            raise

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "products": _rows("products"),
            "sales": _rows("sales"),
            "sale_items": _rows("sale_items"),
            "inventory_movements": _rows("inventory_movements"),
        },
    }
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    return out
