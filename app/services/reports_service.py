"""Read-only analytics and CSV exports for sales, products, and purchasing."""

from __future__ import annotations

import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from app.database.connection import db
from app.services.money import cents_to_float, to_cents
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

    @staticmethod
    def _timestamp_range(start_iso: str, end_iso: str) -> tuple[str, str]:
        """Inclusive date range represented as [start, next_day_start)."""
        start_day = date.fromisoformat(start_iso)
        end_day = date.fromisoformat(end_iso)
        return f"{start_day.isoformat()} 00:00:00", f"{(end_day + timedelta(days=1)).isoformat()} 00:00:00"

    def sales_summary(self, start_date: str, end_date: str) -> dict:
        """Aggregate sales in inclusive date range; net figures subtract refunds booked in the same range."""
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        start_ts, end_ts = self._timestamp_range(a, b)
        row = db.fetchone(
            """
            SELECT COUNT(*) AS invoice_count,
                   COALESCE(SUM(total_amount_cents), CAST(ROUND(COALESCE(SUM(total_amount), 0) * 100.0, 0) AS INTEGER)) AS sales_gross_cents,
                   COALESCE(SUM(subtotal_cents), CAST(ROUND(COALESCE(SUM(subtotal), 0) * 100.0, 0) AS INTEGER)) AS subtotal_total_cents,
                   COALESCE(SUM(discount_amount_cents), CAST(ROUND(COALESCE(SUM(discount_amount), 0) * 100.0, 0) AS INTEGER)) AS discount_total_cents
            FROM sales
            WHERE sale_date >= ? AND sale_date < ?
            """,
            (start_ts, end_ts),
        )
        ref_row = db.fetchone(
            """
            SELECT COALESCE(SUM(total_refund_amount_cents), CAST(ROUND(COALESCE(SUM(total_refund_amount), 0) * 100.0, 0) AS INTEGER)) AS refund_total
            FROM sale_returns
            WHERE return_date >= ? AND return_date < ?
            """,
            (start_ts, end_ts),
        )
        refund_total_cents = int(ref_row["refund_total"] or 0) if ref_row else 0
        refund_total = cents_to_float(refund_total_cents)
        if not row:
            return {
                "invoice_count": 0,
                "sales_gross": 0.0,
                "gross_total": 0.0,
                "refund_total": refund_total,
                "subtotal_total": 0.0,
                "discount_total": 0.0,
                "avg_ticket": 0.0,
            }
        n = int(row["invoice_count"] or 0)
        sales_gross_cents = int(row["sales_gross_cents"] or 0)
        sub_cents = int(row["subtotal_total_cents"] or 0)
        disc_cents = int(row["discount_total_cents"] or 0)
        net_cents = sales_gross_cents - refund_total_cents
        avg = cents_to_float(round(net_cents / n)) if n else 0.0
        return {
            "invoice_count": n,
            "sales_gross": cents_to_float(sales_gross_cents),
            "gross_total": cents_to_float(net_cents),
            "refund_total": refund_total,
            "subtotal_total": cents_to_float(sub_cents),
            "discount_total": cents_to_float(disc_cents),
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
        start_ts, end_ts = self._timestamp_range(a, b)
        sales_rows = db.fetchall(
            """
            SELECT DATE(sale_date) AS day,
                   COUNT(*) AS invoices,
                   COALESCE(SUM(total_amount_cents), CAST(ROUND(COALESCE(SUM(total_amount), 0) * 100.0, 0) AS INTEGER)) AS sales_sum
            FROM sales
            WHERE sale_date >= ? AND sale_date < ?
            GROUP BY DATE(sale_date)
            """,
            (start_ts, end_ts),
        )
        ref_rows = db.fetchall(
            """
            SELECT DATE(return_date) AS day,
                   COALESCE(SUM(total_refund_amount_cents), CAST(ROUND(COALESCE(SUM(total_refund_amount), 0) * 100.0, 0) AS INTEGER)) AS refund_sum
            FROM sale_returns
            WHERE return_date >= ? AND return_date < ?
            GROUP BY DATE(return_date)
            """,
            (start_ts, end_ts),
        )
        by_ref = {str(r["day"]): int(r["refund_sum"] or 0) for r in ref_rows}
        out: list[dict] = []
        for r in sales_rows:
            d = str(r["day"])
            inv = int(r["invoices"] or 0)
            ssum = int(r["sales_sum"] or 0)
            net = cents_to_float(ssum - by_ref.get(d, 0))
            out.append({"day": d, "invoices": inv, "gross_total": net})
        for d, rsum in by_ref.items():
            if not any(str(x["day"]) == d for x in out):
                out.append({"day": d, "invoices": 0, "gross_total": cents_to_float(-rsum)})
        out.sort(key=lambda x: str(x["day"]))
        return out

    def sales_by_payment_method(self, start_date: str, end_date: str) -> list[dict]:
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        start_ts, end_ts = self._timestamp_range(a, b)

        def _norm(m: str | None) -> str:
            x = (m or "").strip().upper()
            return x if x else "—"

        sales_rows = db.fetchall(
            """
            SELECT UPPER(TRIM(COALESCE(payment_method, ''))) AS method,
                   COUNT(*) AS invoices,
                   COALESCE(SUM(total_amount_cents), CAST(ROUND(COALESCE(SUM(total_amount), 0) * 100.0, 0) AS INTEGER)) AS sales_sum
            FROM sales
            WHERE sale_date >= ? AND sale_date < ?
            GROUP BY UPPER(TRIM(COALESCE(payment_method, '')))
            """,
            (start_ts, end_ts),
        )
        ref_rows = db.fetchall(
            """
            SELECT UPPER(TRIM(COALESCE(payment_method, ''))) AS method,
                   COALESCE(SUM(total_refund_amount_cents), CAST(ROUND(COALESCE(SUM(total_refund_amount), 0) * 100.0, 0) AS INTEGER)) AS refund_sum
            FROM sale_returns
            WHERE return_date >= ? AND return_date < ?
            GROUP BY UPPER(TRIM(COALESCE(payment_method, '')))
            """,
            (start_ts, end_ts),
        )
        sales_map: dict[str, tuple[int, int]] = {}
        for r in sales_rows:
            k = _norm(r["method"])
            sales_map[k] = (int(r["invoices"] or 0), int(r["sales_sum"] or 0))
        ref_map: dict[str, int] = {}
        for r in ref_rows:
            k = _norm(r["method"])
            ref_map[k] = ref_map.get(k, 0) + int(r["refund_sum"] or 0)

        keys = set(sales_map) | set(ref_map)
        out: list[dict] = []
        for k in keys:
            inv, sm = sales_map.get(k, (0, 0))
            ref = ref_map.get(k, 0)
            net = cents_to_float(sm - ref)
            out.append({"method": k, "invoices": inv, "gross_total": net})
        out.sort(key=lambda x: to_cents(x["gross_total"]), reverse=True)
        return out

    def top_products_by_revenue(self, start_date: str, end_date: str, limit: int = 25) -> list[dict]:
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        start_ts, end_ts = self._timestamp_range(a, b)
        try:
            lim = int(limit)
            if lim < 1 or lim > 500:
                raise ValueError("Limit must be between 1 and 500.")
        except (ValueError, TypeError):
            raise ValueError("Limit must be a valid integer between 1 and 500.")
        
        rows = db.fetchall(
            """
            SELECT p.id AS product_id, p.code, p.name,
                   COALESCE(sa.qty, 0) - COALESCE(ra.qty, 0) AS qty_sold,
                   COALESCE(sa.rev, 0) - COALESCE(ra.rev, 0) AS revenue
            FROM products p
            LEFT JOIN (
                SELECT si.product_id AS pid,
                       SUM(si.quantity) AS qty,
                       COALESCE(SUM(si.total_cents), CAST(ROUND(COALESCE(SUM(si.total), 0) * 100.0, 0) AS INTEGER)) AS rev
                FROM sale_items si
                JOIN sales s ON s.id = si.sale_id
                WHERE s.sale_date >= ? AND s.sale_date < ?
                GROUP BY si.product_id
            ) sa ON sa.pid = p.id
            LEFT JOIN (
                SELECT sri.product_id AS pid,
                       SUM(sri.quantity_returned) AS qty,
                       COALESCE(SUM(sri.line_refund_amount_cents), CAST(ROUND(COALESCE(SUM(sri.line_refund_amount), 0) * 100.0, 0) AS INTEGER)) AS rev
                FROM sale_return_items sri
                JOIN sale_returns sr ON sr.id = sri.sale_return_id
                WHERE sr.return_date >= ? AND sr.return_date < ?
                GROUP BY sri.product_id
            ) ra ON ra.pid = p.id
            WHERE (COALESCE(sa.rev, 0) - COALESCE(ra.rev, 0)) > 0
            ORDER BY revenue DESC
            LIMIT ?
            """,
            (start_ts, end_ts, start_ts, end_ts, lim),
        )
        return [
            {
                "product_id": int(r["product_id"]),
                "code": r["code"] or "",
                "name": r["name"] or "",
                "qty_sold": float(r["qty_sold"] or 0),
                "revenue": cents_to_float(int(r["revenue"] or 0)),
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
        start_ts, end_ts = self._timestamp_range(a, b)
        try:
            rows = db.fetchall(
                """
                SELECT r.id, r.reference, r.supplier_name, r.supplier_phone, r.supplier_email,
                       r.received_at, r.created_at,
                       (SELECT COUNT(*) FROM purchases p WHERE p.receipt_id = r.id) AS line_count,
                       (SELECT COALESCE(SUM(p.quantity * p.cost_price), 0)
                          FROM purchases p WHERE p.receipt_id = r.id) AS total_value
                FROM purchase_receipts r
                WHERE (
                    (r.received_at IS NOT NULL AND r.received_at >= ? AND r.received_at < ?)
                    OR (r.received_at IS NULL AND r.created_at >= ? AND r.created_at < ?)
                )
                ORDER BY COALESCE(r.received_at, r.created_at) DESC, r.id DESC
                """,
                (start_ts, end_ts, start_ts, end_ts),
            )
            return [dict(r) for r in rows]
        except sqlite3.OperationalError as e:
            raise sqlite3.OperationalError(f"Failed to retrieve purchase receipts: {e}") from e

    def list_sales_for_export(self, start_date: str, end_date: str) -> list[dict]:
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        start_ts, end_ts = self._timestamp_range(a, b)
        rows = db.fetchall(
            """
            SELECT id, invoice_number, sale_date, subtotal, discount_amount,
                   total_amount, payment_method, customer_name, cashier_name
            FROM sales
            WHERE sale_date >= ? AND sale_date < ?
            ORDER BY sale_date DESC, id DESC
            """,
            (start_ts, end_ts),
        )
        return [dict(r) for r in rows]

    def sales_receipts_grouped_by_day(self, start_date: str, end_date: str) -> list[dict]:
        """Sales invoices in range, grouped by calendar day of ``sale_date`` (newest day first)."""
        a = self._validate_iso(start_date)
        b = self._validate_iso(end_date)
        if a > b:
            raise ValueError("Start date must be on or before end date.")
        start_ts, end_ts = self._timestamp_range(a, b)
        rows = db.fetchall(
            """
            SELECT id, invoice_number, sale_date, DATE(sale_date) AS issue_day,
                   subtotal, discount_amount, total_amount, payment_method, customer_name, cashier_name
            FROM sales
            WHERE sale_date >= ? AND sale_date < ?
            ORDER BY issue_day DESC, sale_date DESC, id DESC
            """,
            (start_ts, end_ts),
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
        start_ts, end_ts = self._timestamp_range(a, b)
        rows = db.fetchall(
            """
            SELECT s.invoice_number, DATE(s.sale_date) AS sale_day,
                   p.code AS product_code, p.name AS product_name,
                   si.quantity, si.unit_price, si.total AS line_total
            FROM sale_items si
            JOIN sales s ON s.id = si.sale_id
            JOIN products p ON p.id = si.product_id
            WHERE s.sale_date >= ? AND s.sale_date < ?
            ORDER BY s.sale_date DESC, s.id DESC, si.id
            """,
            (start_ts, end_ts),
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