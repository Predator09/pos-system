import tempfile
import unittest
from pathlib import Path

from app.database.connection import db
from app.database.migrations import DatabaseMigrations
from app.services import backup_service
from app.services.backup_service import BackupService
from app.services.reports_service import ReportsService
from app.services.sales_service import SalesService


class CriticalFlowTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_path = Path(self._tmp.name)
        self._original_db_path = db.db_path
        self._original_backups_dir = backup_service.backups_dir
        self._original_db_backups_dir = backup_service.db_backups_dir

        db.close()
        db.reconfigure(self._tmp_path / "test.sqlite3")
        DatabaseMigrations(db).init_database()
        db.connect()

        backup_service.backups_dir = lambda: self._tmp_path / "backups"
        backup_service.db_backups_dir = lambda: self._tmp_path / "backups" / "db"

    def tearDown(self):
        backup_service.backups_dir = self._original_backups_dir
        backup_service.db_backups_dir = self._original_db_backups_dir
        db.close()
        db.reconfigure(self._original_db_path)
        self._tmp.cleanup()

    def _insert_product(self) -> int:
        cur = db.execute(
            """
            INSERT INTO products (
                name, code, quantity_in_stock, minimum_stock_level, maximum_stock_level,
                cost_price, selling_price, discount_percentage, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("Integration Item", "ITM-001", 10, 1, 100, 10.0, 15.0, 0.0, 1),
        )
        return int(cur.lastrowid)

    def test_sale_return_reports_and_backup_restore_consistency(self):
        product_id = self._insert_product()
        sales = SalesService()
        reports = ReportsService()
        backups = BackupService()

        sale = sales.record_sale(
            cart_items=[
                {
                    "product_id": product_id,
                    "quantity": 2,
                    "unit_price": 15.0,
                    "total": 30.0,
                    "discount_amount": 0.0,
                }
            ],
            payment_info={"method": "CASH", "customer_name": "Walk-in", "cashier_name": "Tester"},
        )
        sale_item_id = int(sale["items"][0]["id"])
        sale_id = int(sale["id"])

        sales.record_return(
            sale_id=sale_id,
            lines=[{"sale_item_id": sale_item_id, "quantity": 1}],
            payment_info={"method": "CASH", "cashier_name": "Tester"},
        )

        report_day = str(sale["sale_date"])[:10]
        summary_before = reports.sales_summary(report_day, report_day)
        product_stock_before = float(
            db.fetchone("SELECT quantity_in_stock FROM products WHERE id = ?", (product_id,))[0]
        )

        self.assertEqual(summary_before["invoice_count"], 1)
        self.assertAlmostEqual(summary_before["sales_gross"], 30.0, places=2)
        self.assertAlmostEqual(summary_before["refund_total"], 15.0, places=2)
        self.assertAlmostEqual(summary_before["gross_total"], 15.0, places=2)
        self.assertAlmostEqual(product_stock_before, 9.0, places=6)

        backup_path = backups.create_full_backup()

        db_files = list((self._tmp_path / "backups" / "db").glob("backup_*.db"))
        self.assertEqual(len(db_files), 1)
        self.assertGreater(db_files[0].stat().st_size, 0)

        db.execute("DELETE FROM sale_returns")
        db.execute("DELETE FROM sales")
        db.execute("UPDATE products SET quantity_in_stock = 0 WHERE id = ?", (product_id,))

        self.assertTrue(backups.restore_from_backup(backup_path))

        summary_after = reports.sales_summary(report_day, report_day)
        product_stock_after = float(
            db.fetchone("SELECT quantity_in_stock FROM products WHERE id = ?", (product_id,))[0]
        )
        return_count = int(db.fetchone("SELECT COUNT(*) FROM sale_returns")[0])
        return_item_count = int(db.fetchone("SELECT COUNT(*) FROM sale_return_items")[0])

        self.assertEqual(summary_after["invoice_count"], summary_before["invoice_count"])
        self.assertAlmostEqual(summary_after["sales_gross"], summary_before["sales_gross"], places=2)
        self.assertAlmostEqual(summary_after["refund_total"], summary_before["refund_total"], places=2)
        self.assertAlmostEqual(summary_after["gross_total"], summary_before["gross_total"], places=2)
        self.assertAlmostEqual(product_stock_after, product_stock_before, places=6)
        self.assertEqual(return_count, 1)
        self.assertEqual(return_item_count, 1)


if __name__ == "__main__":
    unittest.main()
