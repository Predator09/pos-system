import csv
import json
from datetime import datetime
from pathlib import Path

from app.database.connection import db
from app.database.db_backup import backup_database
from app.database.sync import SyncTracker
from app.services.app_logging import get_logger
from app.services.shop_context import backups_dir, db_backups_dir

_PRODUCT_COLUMNS = (
    "id",
    "name",
    "code",
    "barcode",
    "category",
    "description",
    "quantity_in_stock",
    "minimum_stock_level",
    "maximum_stock_level",
    "cost_price",
    "selling_price",
    "discount_percentage",
    "is_active",
    "created_at",
    "updated_at",
)

_SALES_COLUMNS = (
    "id",
    "invoice_number",
    "sale_date",
    "subtotal",
    "subtotal_cents",
    "discount_amount",
    "discount_amount_cents",
    "tax_amount",
    "tax_amount_cents",
    "total_amount",
    "total_amount_cents",
    "payment_method",
    "customer_name",
    "cashier_name",
    "notes",
    "is_synced",
    "created_at",
)

_SALE_ITEM_COLUMNS = (
    "id",
    "sale_id",
    "product_id",
    "quantity",
    "unit_price",
    "unit_price_cents",
    "discount_percentage",
    "total",
    "total_cents",
)

_SALE_RETURN_COLUMNS = (
    "id",
    "sale_id",
    "credit_memo_number",
    "return_date",
    "total_refund_amount",
    "total_refund_amount_cents",
    "payment_method",
    "notes",
    "cashier_name",
    "created_at",
)

_SALE_RETURN_ITEM_COLUMNS = (
    "id",
    "sale_return_id",
    "sale_item_id",
    "product_id",
    "quantity_returned",
    "line_refund_amount",
    "line_refund_amount_cents",
)

_SUPPLIER_COLUMNS = (
    "id",
    "name",
    "phone",
    "email",
    "address",
    "notes",
    "is_active",
    "created_at",
    "updated_at",
)

_PURCHASE_RECEIPT_COLUMNS = (
    "id",
    "reference",
    "supplier_name",
    "notes",
    "received_at",
    "created_at",
    "supplier_phone",
    "supplier_email",
    "supplier_id",
)

_PURCHASE_COLUMNS = (
    "id",
    "product_id",
    "quantity",
    "cost_price",
    "supplier_name",
    "notes",
    "purchase_date",
    "created_at",
    "receipt_id",
)


class BackupService:
    def __init__(self):
        self.backup_dir = backups_dir()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.sync = SyncTracker(db)

    def latest_backup_summary(self) -> str:
        """One-line status for dashboards / settings (newest ``backup_*.json`` by mtime)."""
        try:
            files = list(self.backup_dir.glob("backup_*.json"))
        except OSError:
            return "Backups folder unavailable."
        if not files:
            return "No backups yet."
        latest = max(files, key=lambda p: p.stat().st_mtime)
        try:
            mtime = datetime.fromtimestamp(latest.stat().st_mtime)
            return f"Last backup: {mtime.strftime('%Y-%m-%d %H:%M')} · {latest.name}"
        except OSError:
            return f"Last backup: {latest.name}"

    def create_full_backup(self) -> str:
        """Create complete backup of all data to JSON."""
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "products": [dict(row) for row in db.fetchall("SELECT * FROM products")],
            "suppliers": [dict(row) for row in db.fetchall("SELECT * FROM suppliers")],
            "sales": [dict(row) for row in db.fetchall("SELECT * FROM sales")],
            "sale_items": [dict(row) for row in db.fetchall("SELECT * FROM sale_items")],
            "sale_returns": [dict(row) for row in db.fetchall("SELECT * FROM sale_returns")],
            "sale_return_items": [dict(row) for row in db.fetchall("SELECT * FROM sale_return_items")],
            "purchase_receipts": [dict(row) for row in db.fetchall("SELECT * FROM purchase_receipts")],
            "purchases": [dict(row) for row in db.fetchall("SELECT * FROM purchases")],
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.json"

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, default=str)

        sqlite_backup = db_backups_dir() / f"backup_{timestamp}.db"
        try:
            backup_database(db.db_path, sqlite_backup)
        except Exception as exc:
            get_logger().warning("SQLite file backup failed: %s", exc)

        return str(backup_file)

    def create_csv_export(self, report_type: str) -> str:
        """Export report to CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if report_type == "sales":
            results = db.fetchall(
                """
                SELECT s.*, COUNT(si.id) as item_count
                FROM sales s
                LEFT JOIN sale_items si ON s.id = si.sale_id
                GROUP BY s.id
                ORDER BY s.sale_date DESC
                """
            )

            export_file = self.backup_dir / f"sales_export_{timestamp}.csv"
            with open(export_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Invoice",
                        "Date",
                        "Subtotal",
                        "Discount",
                        "Total",
                        "Items",
                        "Payment Method",
                        "Staff",
                    ]
                )
                for row in results:
                    writer.writerow(
                        [
                            row["invoice_number"],
                            row["sale_date"],
                            row["subtotal"],
                            row["discount_amount"],
                            row["total_amount"],
                            row["item_count"],
                            row["payment_method"],
                            row["cashier_name"] if "cashier_name" in row.keys() else "",
                        ]
                    )

        elif report_type == "inventory":
            results = db.fetchall("SELECT * FROM products ORDER BY name")

            export_file = self.backup_dir / f"inventory_export_{timestamp}.csv"
            with open(export_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["Code", "Name", "Category", "Stock", "Min Level", "Cost", "Price"]
                )
                for row in results:
                    writer.writerow(
                        [
                            row["code"],
                            row["name"],
                            row["category"],
                            row["quantity_in_stock"],
                            row["minimum_stock_level"],
                            row["cost_price"],
                            row["selling_price"],
                        ]
                    )

        else:
            raise ValueError(f"Unknown report_type: {report_type!r} (use 'sales' or 'inventory')")

        return str(export_file)

    def auto_backup_daily(self) -> None:
        """At most one automatic JSON backup per calendar day (avoids UI stall on every login)."""
        today = datetime.now().strftime("%Y%m%d")
        if any(self.backup_dir.glob(f"backup_{today}_*.json")):
            return
        self.create_full_backup()

    def restore_from_backup(self, backup_file: str) -> bool:
        """Restore database from backup file."""
        if db.connection is None:
            db.connect()
        conn = db.connection
        path = Path(backup_file)
        try:
            with open(path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)

            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("PRAGMA foreign_keys = OFF")
            cur.execute("DELETE FROM sale_items")
            cur.execute("DELETE FROM sale_return_items")
            cur.execute("DELETE FROM sale_returns")
            cur.execute("DELETE FROM sales")
            cur.execute("DELETE FROM purchases")
            cur.execute("DELETE FROM purchase_receipts")
            cur.execute("DELETE FROM suppliers")
            cur.execute("DELETE FROM products")
            cur.execute("DELETE FROM sync_log")

            _insert_rows(cur, "products", _PRODUCT_COLUMNS, backup_data.get("products", []))
            _insert_rows(cur, "suppliers", _SUPPLIER_COLUMNS, backup_data.get("suppliers", []))
            _insert_rows(
                cur,
                "purchase_receipts",
                _PURCHASE_RECEIPT_COLUMNS,
                backup_data.get("purchase_receipts", []),
            )
            _insert_rows(cur, "sales", _SALES_COLUMNS, backup_data.get("sales", []))
            _insert_rows(cur, "sale_items", _SALE_ITEM_COLUMNS, backup_data.get("sale_items", []))
            _insert_rows(
                cur,
                "sale_returns",
                _SALE_RETURN_COLUMNS,
                backup_data.get("sale_returns", []),
            )
            _insert_rows(
                cur,
                "sale_return_items",
                _SALE_RETURN_ITEM_COLUMNS,
                backup_data.get("sale_return_items", []),
            )
            _insert_rows(cur, "purchases", _PURCHASE_COLUMNS, backup_data.get("purchases", []))

            for table in (
                "products",
                "suppliers",
                "purchase_receipts",
                "sales",
                "sale_items",
                "sale_returns",
                "sale_return_items",
                "purchases",
            ):
                _reset_sqlite_sequence(cur, table)

            cur.execute("PRAGMA foreign_keys = ON")
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Restore failed: {e}")
            return False


def _insert_rows(cur, table: str, columns: tuple, rows: list) -> None:
    if not rows:
        return
    placeholders = ",".join("?" * len(columns))
    col_sql = ",".join(columns)
    sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"
    for row in rows:
        cur.execute(sql, tuple(row.get(c) for c in columns))


def _reset_sqlite_sequence(cur, table: str) -> None:
    cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
    max_id = cur.fetchone()[0]
    cur.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
    cur.execute("INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table, max_id))
