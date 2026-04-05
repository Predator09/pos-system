from datetime import date, datetime, timedelta

from app.database.connection import db
from app.database.sync import SyncOperation, SyncTracker


class SalesService:
    def __init__(self):
        self.sync = SyncTracker(db)

    def calculate_cart_total(self, cart_items: list) -> dict:
        """Calculate totals from cart items."""
        subtotal = sum(item["quantity"] * item["unit_price"] for item in cart_items)
        discount_amount = sum(item.get("discount_amount", 0) for item in cart_items)
        taxable_base = subtotal - discount_amount
        total = taxable_base

        return {
            "subtotal": round(subtotal, 2),
            "discount_amount": round(discount_amount, 2),
            "tax_amount": 0.0,
            "total": round(total, 2),
        }

    def record_sale(self, cart_items: list, payment_info: dict) -> dict:
        """Record sale to local database (completely offline)."""

        # Calculate totals
        totals = self.calculate_cart_total(cart_items)

        # Generate invoice number (local)
        invoice = self._generate_invoice_number()

        # Insert sale
        cursor = db.execute(
            """
            INSERT INTO sales (invoice_number, subtotal, discount_amount, tax_amount, total_amount, payment_method, customer_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice,
                totals["subtotal"],
                totals["discount_amount"],
                totals["tax_amount"],
                totals["total"],
                payment_info.get("method", "CASH"),
                payment_info.get("customer_name", ""),
            ),
        )

        sale_id = cursor.lastrowid

        # Insert sale items
        for item in cart_items:
            db.execute(
                """
                INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, total)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sale_id, item["product_id"], item["quantity"], item["unit_price"], item["total"]),
            )

            # Update product stock
            db.execute(
                """
                UPDATE products SET quantity_in_stock = quantity_in_stock - ? WHERE id = ?
                """,
                (item["quantity"], item["product_id"]),
            )

        # Log for sync
        self.sync.log_change("sales", sale_id, SyncOperation.CREATE)

        return self.get_sale(sale_id)

    def get_sale(self, sale_id: int) -> dict:
        """Get sale details (local only)."""
        sale = db.fetchone("SELECT * FROM sales WHERE id = ?", (sale_id,))
        if not sale:
            return None

        sale_dict = dict(sale)
        items = db.fetchall(
            """
            SELECT si.*, p.name, p.code FROM sale_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.sale_id = ?
            """,
            (sale_id,),
        )

        sale_dict["items"] = [dict(item) for item in items]
        return sale_dict

    def get_sales_by_date(self, start_date, end_date) -> list:
        """Get sales for date range (local only)."""
        results = db.fetchall(
            """
            SELECT * FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            ORDER BY sale_date DESC
            """,
            (start_date, end_date),
        )
        return [dict(row) for row in results]

    def aggregate_sales_range(self, start_date: str, end_date: str) -> dict:
        """Invoice count and gross total for inclusive ``DATE(sale_date)`` range."""
        rows = self.get_sales_by_date(start_date, end_date)
        gross = sum(float(r.get("total_amount") or 0) for r in rows)
        return {
            "invoice_count": len(rows),
            "gross_total": round(gross, 2),
        }

    def aggregate_sales_metrics_range(self, start_date: str, end_date: str) -> dict:
        """Single-row aggregates for receipt-style period summaries."""
        row = db.fetchone(
            """
            SELECT COUNT(*) AS invoice_count,
                   COALESCE(SUM(total_amount), 0) AS gross_total,
                   COALESCE(SUM(subtotal), 0) AS subtotal_sum,
                   COALESCE(SUM(discount_amount), 0) AS discount_sum
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            """,
            (start_date, end_date),
        )
        if not row:
            return {
                "invoice_count": 0,
                "gross_total": 0.0,
                "subtotal_sum": 0.0,
                "discount_sum": 0.0,
            }
        return {
            "invoice_count": int(row["invoice_count"] or 0),
            "gross_total": round(float(row["gross_total"] or 0), 2),
            "subtotal_sum": round(float(row["subtotal_sum"] or 0), 2),
            "discount_sum": round(float(row["discount_sum"] or 0), 2),
        }

    def daily_gross_by_date(self, start_date: str, end_date: str) -> list[tuple[str, float]]:
        """Each calendar day in range with gross (0.0 if no sales)."""
        rows = db.fetchall(
            """
            SELECT DATE(sale_date) AS d, COALESCE(SUM(total_amount), 0) AS g
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            GROUP BY DATE(sale_date)
            ORDER BY d
            """,
            (start_date, end_date),
        )
        by_day = {str(r["d"]): float(r["g"] or 0) for r in rows}
        cur = date.fromisoformat(start_date[:10])
        end = date.fromisoformat(end_date[:10])
        out: list[tuple[str, float]] = []
        while cur <= end:
            k = cur.isoformat()
            out.append((k, by_day.get(k, 0.0)))
            cur += timedelta(days=1)
        return out

    def chart_series_for_overview(self, start_date: str, end_date: str) -> tuple[list[tuple[str, float]], str]:
        """
        Points for the dashboard bar chart: daily buckets if range ≤ 45 days,
        else one bar per calendar month in the range (zero-filled).
        """
        sd = date.fromisoformat(start_date[:10])
        ed = date.fromisoformat(end_date[:10])
        n = (ed - sd).days + 1
        s, e = start_date[:10], end_date[:10]
        if n <= 45:
            return self.daily_gross_by_date(s, e), "Daily gross"
        rows = db.fetchall(
            """
            SELECT strftime('%Y-%m', sale_date) AS ym,
                   COALESCE(SUM(total_amount), 0) AS g
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            GROUP BY ym
            ORDER BY ym
            """,
            (s, e),
        )
        by_m = {str(r["ym"]): float(r["g"] or 0) for r in rows}
        pts: list[tuple[str, float]] = []
        y, m = sd.year, sd.month
        while date(y, m, 1) <= ed:
            key = f"{y:04d}-{m:02d}"
            pts.append((key, by_m.get(key, 0.0)))
            m += 1
            if m > 12:
                m = 1
                y += 1
        return pts, "Monthly gross"

    def get_todays_totals(self) -> dict:
        """Aggregate today's sales for the dashboard (local SQLite)."""
        today = date.today().isoformat()
        return self.aggregate_sales_range(today, today)

    def cash_total_for_range(self, start_date: str, end_date: str) -> float:
        """Sum of CASH sales in inclusive date range."""
        row = db.fetchone(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS s
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
              AND UPPER(TRIM(COALESCE(payment_method, ''))) = 'CASH'
            """,
            (start_date, end_date),
        )
        if not row:
            return 0.0
        return round(float(row["s"] or 0), 2)

    def get_todays_cash_total(self) -> float:
        """Sum of today's sales paid in cash (proxy for drawer intake this session)."""
        today = date.today().isoformat()
        return self.cash_total_for_range(today, today)

    def get_recent_sales(self, limit: int = 5) -> list:
        """Latest sales rows for dashboard activity (any day)."""
        results = db.fetchall(
            """
            SELECT * FROM sales
            ORDER BY datetime(sale_date) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in results]

    def _generate_invoice_number(self) -> str:
        """Generate invoice number locally."""
        result = db.fetchone("SELECT MAX(id) FROM sales")
        next_id = (result[0] or 0) + 1
        today = datetime.now().strftime("%Y%m%d")
        return f"INV{today}{next_id:05d}"
