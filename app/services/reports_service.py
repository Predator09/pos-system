"""Read-only analytics and CSV exports for sales, products, and purchasing."""

from __future__ import annotations

import csv
import sqlite3
from datetime import date
from pathlib import Path

from app.database.connection import db
from app.ui.date_display import DISPLAY_DATE_FMT, format_iso_date_as_display, parse_date_input


def format_sales_calendar_day(iso_day: str | None) -> str:
    """Turn ``YYYY-MM-DD`` into a weekday line with ``DD-MM-YYYY`` (day first)."""
    raw = str(iso_day or "").strip()[:10]
    if len(raw) != 10:
        return str(iso_day or "").strip() or "—"
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        return str(iso_day or "")
    return f"{d.strftime('%A')}, {d.strftime(DISPLAY_DATE_FMT)}"


def format_report_period_title(start_iso: str, end_iso: str) -> str:
    """Short heading for the reports header (single day vs range)."""
    a = str(start_iso or "").strip()[:10]
    b = str(end_iso or "").strip()[:10]
    if len(a) != 10 or len(b) != 10:
        return f"{start_iso} – {end_iso}".strip(" –") or "—"

    if a == b:
        return format_sales_calendar_day(a)
    try:
        da, db = date.fromisoformat(a), date.fromisoformat(b)
    except ValueError:
        return f"{format_iso_date_as_display(a)} – {format_iso_date_as_display(b)}"
    return f"{da.strftime(DISPLAY_DATE_FMT)} – {db.strftime(DISPLAY_DATE_FMT)}"


class ReportsService:
    """SQL-backed reports; no mutations."""

    @staticmethod
    def _validate_iso(d: str) -> str:
        return parse_date_input(d)

    def sales_summary(self, start_date: str, end_date: str) -> dict:
        """Aggregate sales in inclusive date range (on ``sale_date``)."""
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        row = db.fetchone(
            """
            SELECT COUNT(*) AS invoice_count,
                   COALESCE(SUM(total_amount), 0) AS gross_total,
                   COALESCE(SUM(subtotal), 0) AS subtotal_total,
                   COALESCE(SUM(discount_amount), 0) AS discount_total
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            """,
            (a, b),
        )
        if not row:
            return {
                "invoice_count": 0,
                "gross_total": 0.0,
                "subtotal_total": 0.0,
                "discount_total": 0.0,
                "avg_ticket": 0.0,
            }
        n = int(row["invoice_count"] or 0)
        gross = float(row["gross_total"] or 0)
        sub = float(row["subtotal_total"] or 0)
        disc = float(row["discount_total"] or 0)
        avg = round(gross / n, 2) if n else 0.0
        return {
            "invoice_count": n,
            "gross_total": round(gross, 2),
            "subtotal_total": round(sub, 2),
            "discount_total": round(disc, 2),
            "avg_ticket": avg,
        }

    def get_sale_by_invoice_number(self, raw: str) -> dict | None:
        """Return one sale row if ``invoice_number`` matches (case-insensitive trim)."""
        inv = (raw or "").strip()
        if not inv:
            return None
        row = db.fetchone(
            """
            SELECT * FROM sales
            WHERE UPPER(TRIM(invoice_number)) = UPPER(TRIM(?))
            LIMIT 1
            """,
            (inv,),
        )
        return dict(row) if row else None

    def sales_by_day(self, start_date: str, end_date: str) -> list[dict]:
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        rows = db.fetchall(
            """
            SELECT DATE(sale_date) AS day,
                   COUNT(*) AS invoices,
                   COALESCE(SUM(total_amount), 0) AS gross_total
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            GROUP BY DATE(sale_date)
            ORDER BY day
            """,
            (a, b),
        )
        return [dict(r) for r in rows]

    def sales_by_payment_method(self, start_date: str, end_date: str) -> list[dict]:
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        rows = db.fetchall(
            """
            SELECT UPPER(TRIM(COALESCE(payment_method, ''))) AS method,
                   COUNT(*) AS invoices,
                   COALESCE(SUM(total_amount), 0) AS gross_total
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            GROUP BY UPPER(TRIM(COALESCE(payment_method, '')))
            ORDER BY gross_total DESC
            """,
            (a, b),
        )
        out = []
        for r in rows:
            m = (r["method"] or "").strip() or "—"
            out.append(
                {
                    "method": m,
                    "invoices": int(r["invoices"] or 0),
                    "gross_total": round(float(r["gross_total"] or 0), 2),
                }
            )
        return out

    def top_products_by_revenue(self, start_date: str, end_date: str, limit: int = 25) -> list[dict]:
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        try:
            lim = int(limit)
            if lim < 1 or lim > 500:
                raise ValueError("Limit must be between 1 and 500.")
        except (ValueError, TypeError):
            raise ValueError("Limit must be a valid integer between 1 and 500.")
        
        rows = db.fetchall(
            """
            SELECT p.id AS product_id, p.code, p.name,
                   SUM(si.quantity) AS qty_sold,
                   SUM(si.total) AS revenue
            FROM sale_items si
            JOIN sales s ON s.id = si.sale_id
            JOIN products p ON p.id = si.product_id
            WHERE DATE(s.sale_date) BETWEEN ? AND ?
            GROUP BY p.id, p.code, p.name
            ORDER BY revenue DESC
            LIMIT ?
            """,
            (a, b, lim),
        )
        return [
            {
                "product_id": int(r["product_id"]),
                "code": r["code"] or "",
                "name": r["name"] or "",
                "qty_sold": float(r["qty_sold"] or 0),
                "revenue": round(float(r["revenue"] or 0), 2),
            }
            for r in rows
        ]

    def inventory_valuation_snapshot(self) -> dict:
        """On-hand units, retail and cost value, and profit (retail − cost) for active lines."""
        row = db.fetchone(
            """
            SELECT COUNT(*) AS skus,
                   COALESCE(SUM(quantity_in_stock), 0) AS units,
                   COALESCE(SUM(selling_price * quantity_in_stock), 0) AS retail_value,
                   COALESCE(SUM(cost_price * quantity_in_stock), 0) AS cost_value
            FROM products
            WHERE is_active = 1
            """
        )
        if not row:
            return {"skus": 0, "units": 0.0, "retail_value": 0.0, "cost_value": 0.0, "profit": 0.0}
        retail = float(row["retail_value"] or 0)
        cost = float(row["cost_value"] or 0)
        return {
            "skus": int(row["skus"] or 0),
            "units": round(float(row["units"] or 0), 2),
            "retail_value": round(retail, 2),
            "cost_value": round(cost, 2),
            "profit": round(retail - cost, 2),
        }

    def purchase_receipts_in_range(self, start_date: str, end_date: str) -> list[dict]:
        """GRN headers received in range (``received_at``)."""
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        try:
            rows = db.fetchall(
                """
                SELECT r.id, r.reference, r.supplier_name, r.supplier_phone, r.supplier_email,
                       r.received_at, r.created_at,
                       (SELECT COUNT(*) FROM purchases p WHERE p.receipt_id = r.id) AS line_count,
                       (SELECT COALESCE(SUM(p.quantity * p.cost_price), 0)
                          FROM purchases p WHERE p.receipt_id = r.id) AS total_value
                FROM purchase_receipts r
                WHERE DATE(COALESCE(r.received_at, r.created_at)) BETWEEN ? AND ?
                ORDER BY COALESCE(r.received_at, r.created_at) DESC, r.id DESC
                """,
                (a, b),
            )
            return [dict(r) for r in rows]
        except sqlite3.OperationalError as e:
            raise sqlite3.OperationalError(f"Failed to retrieve purchase receipts: {e}") from e

    def list_sales_for_export(self, start_date: str, end_date: str) -> list[dict]:
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        rows = db.fetchall(
            """
            SELECT id, invoice_number, sale_date, subtotal, discount_amount,
                   total_amount, payment_method, customer_name, cashier_name
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            ORDER BY sale_date DESC, id DESC
            """,
            (a, b),
        )
        return [dict(r) for r in rows]

    def sales_receipts_grouped_by_day(self, start_date: str, end_date: str) -> list[dict]:
        """Sales invoices in range, grouped by calendar day of ``sale_date`` (newest day first)."""
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        rows = db.fetchall(
            """
            SELECT id, invoice_number, sale_date, DATE(sale_date) AS issue_day,
                   subtotal, discount_amount, total_amount, payment_method, customer_name, cashier_name
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            ORDER BY issue_day DESC, sale_date DESC, id DESC
            """,
            (a, b),
        )
        out: list[dict] = []
        cur: str | None = None
        bucket: list[dict] = []
        for r in rows:
            d = dict(r)
            day = str(d.get("issue_day") or "").strip()[:10]
            if len(day) != 10:
                sd = d.get("sale_date")
                day = str(sd or "")[:10] if sd else ""
            if cur != day:
                if bucket and cur is not None:
                    out.append({"day": cur, "receipts": bucket})
                cur = day
                bucket = []
            bucket.append(d)
        if bucket and cur is not None:
            out.append({"day": cur, "receipts": bucket})
        return out

    def list_sale_lines_for_export(self, start_date: str, end_date: str) -> list[dict]:
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        rows = db.fetchall(
            """
            SELECT s.invoice_number, DATE(s.sale_date) AS sale_day,
                   p.code AS product_code, p.name AS product_name,
                   si.quantity, si.unit_price, si.total AS line_total
            FROM sale_items si
            JOIN sales s ON s.id = si.sale_id
            JOIN products p ON p.id = si.product_id
            WHERE DATE(s.sale_date) BETWEEN ? AND ?
            ORDER BY s.sale_date DESC, s.id DESC, si.id
            """,
            (a, b),
        )
        return [dict(r) for r in rows]

    @staticmethod
    def export_csv(path: str | Path, headers: tuple[str, ...], rows: list[dict]) -> str:
        """Write rows to UTF-8 CSV; returns path string."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            for row in rows:
                w.writerow(tuple("" if row.get(h) is None else str(row.get(h, "")) for h in headers))
        return str(p)

    def export_sales_csv(self, path: str | Path, start_date: str, end_date: str) -> str:
        rows = self.list_sales_for_export(start_date, end_date)
        headers = (
            "invoice_number",
            "sale_date",
            "subtotal",
            "discount_amount",
            "total_amount",
            "payment_method",
            "customer_name",
            "cashier_name",
        )
        return self.export_csv(path, headers, rows)

    def export_sale_lines_csv(self, path: str | Path, start_date: str, end_date: str) -> str:
        rows = self.list_sale_lines_for_export(start_date, end_date)
        headers = (
            "invoice_number",
            "sale_day",
            "product_code",
            "product_name",
            "quantity",
            "unit_price",
            "line_total",
        )
        return self.export_csv(path, headers, rows)