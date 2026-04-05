from enum import Enum


class SyncOperation(Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class SyncTracker:
    def __init__(self, db_connection):
        self.db = db_connection

    def log_change(self, table_name: str, record_id: int, operation: SyncOperation):
        """Log a change for later sync."""
        self.db.execute(
            """
            INSERT INTO sync_log (table_name, record_id, operation)
            VALUES (?, ?, ?)
            """,
            (table_name, record_id, operation.value),
        )

    def get_pending_changes(self):
        """Get all unsynced changes."""
        return self.db.fetchall(
            """
            SELECT * FROM sync_log WHERE synced = 0 ORDER BY timestamp
            """
        )

    def mark_synced(self, sync_log_id: int):
        """Mark a change as synced."""
        self.db.execute(
            """
            UPDATE sync_log SET synced = 1 WHERE id = ?
            """,
            (sync_log_id,),
        )

    def get_unsynced_sales(self):
        """Get all sales not yet synced (for backup)."""
        return self.db.fetchall(
            """
            SELECT * FROM sales WHERE is_synced = 0 ORDER BY sale_date
            """
        )

    def mark_sales_synced(self, sale_ids: list):
        """Mark sales as synced."""
        for sale_id in sale_ids:
            self.db.execute(
                """
                UPDATE sales SET is_synced = 1 WHERE id = ?
                """,
                (sale_id,),
            )
