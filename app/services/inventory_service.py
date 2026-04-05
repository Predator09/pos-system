"""Inventory-facing metrics for dashboards (delegates to SQLite)."""

from __future__ import annotations

from app.database.connection import db


class InventoryService:
    """Stock and catalog counts for reporting surfaces."""

    def get_low_stock_count(self, threshold: int = 10) -> int:
        """Count active products with on-hand quantity strictly below threshold."""
        row = db.fetchone(
            """
            SELECT COUNT(*) AS n
            FROM products
            WHERE is_active = 1 AND quantity_in_stock < ?
            """,
            (threshold,),
        )
        return int(row["n"]) if row else 0

    def get_active_product_count(self) -> int:
        row = db.fetchone(
            "SELECT COUNT(*) AS n FROM products WHERE is_active = 1",
        )
        return int(row["n"]) if row else 0
