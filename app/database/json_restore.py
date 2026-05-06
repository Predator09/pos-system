"""Restore key tables from JSON (versioned ``backup_to_json`` or flat table keys)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.services.app_logging import get_logger


def restore_from_json(json_file, db_connection) -> None:
    """Load ``json_file`` and replace rows in ``products``, ``sales``, ``sale_items``,
    and ``inventory_movements`` (when that table exists).

    Deletes existing rows in those tables first (FK-safe order), then inserts from JSON
    inside a single transaction. Callers must not rely on other tables remaining
    consistent with replaced product/sale IDs.

    Expects either ``{"data": {"products": [...], ...}}`` or top-level table keys.
    """
    path = Path(json_file)
    log = get_logger()
    log.info("Versioned JSON restore started: %s", path)
    if not path.is_file():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw.get("data"), dict):
        data = raw["data"]
    else:
        data = raw

    products = data.get("products") or []
    sales = data.get("sales") or []
    sale_items = data.get("sale_items") or []
    inv_movements = data.get("inventory_movements") or []

    if db_connection.connection is None:
        db_connection.connect()
    conn = db_connection.connection
    cur = conn.cursor()

    def _delete_if_table(name: str) -> None:
        try:
            cur.execute(f"DELETE FROM {name}")
        except sqlite3.OperationalError as exc:
            if name == "inventory_movements" and "no such table" in str(exc).lower():
                return
            raise

    def _insert_rows(table: str, rows: list[dict]) -> None:
        if not rows:
            return
        cols = list(rows[0].keys())
        placeholders = ",".join("?" * len(cols))
        col_sql = ",".join(cols)
        sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"
        for row in rows:
            cur.execute(sql, tuple(row.get(c) for c in cols))

    def _reset_sequence(table: str) -> None:
        cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
        max_id = cur.fetchone()[0]
        cur.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        cur.execute("INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table, max_id))

    try:
        cur.execute("BEGIN IMMEDIATE")
        cur.execute("PRAGMA foreign_keys = OFF")

        _delete_if_table("sale_items")
        _delete_if_table("sales")
        _delete_if_table("inventory_movements")
        _delete_if_table("products")

        _insert_rows("products", products)
        _insert_rows("sales", sales)
        _insert_rows("sale_items", sale_items)

        try:
            if inv_movements:
                _insert_rows("inventory_movements", inv_movements)
        except sqlite3.OperationalError as exc:
            if "no such table" in str(exc).lower() and "inventory_movements" in str(exc).lower():
                if inv_movements:
                    raise sqlite3.OperationalError(
                        "inventory_movements rows present but table does not exist"
                    ) from exc
            raise

        cur.execute("PRAGMA foreign_keys = ON")

        for tbl in ("products", "sales", "sale_items"):
            _reset_sequence(tbl)
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            ("inventory_movements",),
        )
        if cur.fetchone():
            _reset_sequence("inventory_movements")

        conn.commit()
        log.info("Versioned JSON restore succeeded: %s", path)
    except Exception:
        conn.rollback()
        log.exception("Versioned JSON restore failed: %s", path)
        raise
