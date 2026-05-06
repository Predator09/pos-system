"""m002 — add optional ``discount`` column if missing (idempotent)."""

VALIDATION_MARKERS = [
    {"type": "column_exists", "table": "sale_items", "column": "discount"},
]


def _column_names(conn, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def run(db) -> None:
    """Add ``sale_items.discount`` only when absent; safe to re-run."""
    conn = db.connection
    table = "sale_items"
    col = "discount"
    if col in _column_names(conn, table):
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} REAL DEFAULT 0")
