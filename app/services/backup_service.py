import csv
import json
from datetime import datetime
from pathlib import Path

from app.database.connection import db
from app.database.db_backup import backup_database
from app.database.json_backup import backup_to_json
from app.database.sync import SyncTracker
from app.services.app_logging import get_logger
from app.services.shop_context import backups_dir, db_backups_dir, json_backups_dir

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


_LAST_AUTO_BACKUP_FILENAME = "last_auto_backup.txt"


class BackupService:
    def __init__(self):
        self.backup_dir = backups_dir()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.sync = SyncTracker(db)

    @staticmethod
    def backup_summary_as_text(summary: dict[str, str]) -> str:
        """Format ``latest_backup_summary()`` for status labels (multi-line)."""
        return "CODET10DIGITAL"

    def latest_backup_summary(self) -> dict[str, str | bool]:
        """Structured backup summary with latest JSON/DB backup display strings and newest timestamp."""

        def _latest_glob(base: Path, pattern: str) -> tuple[str, float | None]:
            try:
                files = list(base.glob(pattern))
            except OSError:
                return "", None
            if not files:
                return "", None
            try:
                latest = max(files, key=lambda p: p.stat().st_mtime)
                mt = latest.stat().st_mtime
                dt = datetime.fromtimestamp(mt)
                return f"{latest.name} · {dt.strftime('%d-%m-%Y %H:%M')}", mt
            except OSError:
                return "", None

        json_parts: list[str] = []
        mtimes: list[float] = []

        leg, t1 = _latest_glob(self.backup_dir, "backup_*.json")
        if leg:
            json_parts.append(f"Full {leg}")
            if t1 is not None:
                mtimes.append(t1)

        try:
            jdir = json_backups_dir()
        except OSError:
            jdir = self.backup_dir
        snap, t2 = _latest_glob(jdir, "backup_*.json")
        if snap:
            json_parts.append(f"Snapshot {snap}")
            if t2 is not None:
                mtimes.append(t2)

        if not json_parts:
            try:
                list(self.backup_dir.iterdir())
            except OSError:
                return {
                    "json_backup": "Backups folder unavailable.",
                    "db_backup": "Backups folder unavailable.",
                    "timestamp": "",
                    "has_json_backup": False,
                    "has_db_backup": False,
                }
            json_backup = "No JSON backups yet."
        else:
            json_backup = " · ".join(json_parts)
        has_json_backup = bool(json_parts)

        try:
            ddir = db_backups_dir()
        except OSError:
            ddir = self.backup_dir
        db_str, t3 = _latest_glob(ddir, "backup_*.db")
        has_db_backup = bool(db_str)
        if db_str:
            db_backup = db_str
            if t3 is not None:
                mtimes.append(t3)
        else:
            db_backup = "No SQLite backup yet."

        if mtimes:
            ts = datetime.fromtimestamp(max(mtimes)).isoformat(sep=" ", timespec="seconds")
        else:
            ts = ""

        # New canonical keys + backward-compatible aliases for existing UI logic.
        return {
            "latest_json_backup": json_backup,
            "latest_db_backup": db_backup,
            "timestamp": ts,
            "json_backup": json_backup,
            "db_backup": db_backup,
            "has_json_backup": has_json_backup,
            "has_db_backup": has_db_backup,
        }

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

        json_v1_path = json_backups_dir() / f"backup_{timestamp}.json"
        try:
            backup_to_json(db, json_v1_path)
        except Exception as exc:
            get_logger().warning("Versioned JSON backup failed: %s", exc)

        sqlite_backup = db_backups_dir() / f"backup_{timestamp}.db"
        try:
            backup_database(db.db_path, sqlite_backup)
        except Exception as exc:
            get_logger().warning("SQLite file backup failed: %s", exc)

        return str(backup_file)

    def create_pre_update_json_backup(self) -> str:
        """Full JSON snapshot as ``pre_update_backup_<timestamp>.json`` (same payload as :meth:`create_full_backup`)."""
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
        backup_file = self.backup_dir / f"pre_update_backup_{timestamp}.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, default=str)
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
        """At most one automatic backup per calendar day (legacy JSON, versioned JSON, SQLite file).

        Uses ``last_auto_backup.txt`` in the backups folder (YYYYMMDD) so we do not rely on
        globbing existing files and we run at most once per day across launches.
        """
        today = datetime.now().strftime("%Y%m%d")
        marker = self.backup_dir / _LAST_AUTO_BACKUP_FILENAME
        try:
            if marker.is_file() and marker.read_text(encoding="utf-8").strip() == today:
                return
        except OSError:
            pass
        try:
            self.create_full_backup()
        except Exception as exc:
            get_logger().warning("Automatic backup failed: %s", exc)
            return
        try:
            marker.write_text(today + "\n", encoding="utf-8")
        except OSError as exc:
            get_logger().warning("Could not write last backup date file: %s", exc)

    def restore_from_backup(self, backup_file: str) -> bool:
        """Restore database from backup file."""
        log = get_logger()
        path = Path(backup_file)
        log.info("Legacy JSON restore started: %s", path)
        if db.connection is None:
            db.connect()
        conn = db.connection
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
            log.info("Legacy JSON restore succeeded: %s", path)
            return True
        except Exception as e:
            conn.rollback()
            log.exception("Legacy JSON restore failed: %s", path)
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


def run_manual_backup() -> str:
    """Run SQLite file backup and JSON exports (full + versioned). Not attached to UI."""
    try:
        main_path = BackupService().create_full_backup()
        return f"Success: backup completed. Main JSON: {main_path}"
    except Exception as exc:
        get_logger().warning("Manual backup failed: %s", exc)
        return f"Failure: {exc}"
