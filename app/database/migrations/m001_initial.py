"""Sample migration m001 — validates the runner (isolated dummy table only)."""

VALIDATION_MARKERS = [
    {"type": "table_exists", "table": "migration_smoke_marker"},
]


def run(db) -> None:
    # Example: create a dummy table (does not alter existing POS tables).
    conn = db.connection
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS migration_smoke_marker (
            id INTEGER PRIMARY KEY,
            note TEXT
        )
        """
    )
