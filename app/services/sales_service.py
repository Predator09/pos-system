import sqlite3
from datetime import date, datetime, timedelta

from app.database.connection import db
from app.database.sync import SyncOperation, SyncTracker
from app.services.app_logging import log_exception
from app.services.audit_service import AuditService
from app.services.money import cents_to_float, decimal_money, to_cents


def _local_sale_timestamp() -> str:
    """Wall-clock time on this PC, for ``sales.sale_date`` (local business midnight = new day)."""
    return datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def cashier_display_name(user: dict | None) -> str:
    """Label for receipts: full name if set, else username."""
    if not user:
        return ""
    fn = (user.get("full_name") or "").strip()
    if fn:
        return fn
    return (user.get("username") or "").strip()


class SalesService:
    def __init__(self):
        self.sync = SyncTracker(db)
        self.audit = AuditService()

    def calculate_cart_total(self, cart_items: list) -> dict:
        """Calculate totals from cart items."""
        subtotal_cents = sum(
            to_cents(decimal_money(item["quantity"]) * decimal_money(item["unit_price"]))
            for item in cart_items
        )
        discount_amount_cents = sum(to_cents(item.get("discount_amount", 0)) for item in cart_items)
        total_cents = subtotal_cents - discount_amount_cents

        return {
            "subtotal": cents_to_float(subtotal_cents),
            "subtotal_cents": subtotal_cents,
            "discount_amount": cents_to_float(discount_amount_cents),
            "discount_amount_cents": discount_amount_cents,
            "tax_amount": 0.0,
            "tax_amount_cents": 0,
            "total": cents_to_float(total_cents),
            "total_cents": total_cents,
        }

    def record_sale(self, cart_items: list, payment_info: dict) -> dict:
        """Record sale to local database (completely offline).

        Each sale is stamped with the PC's **local** date and time so a new calendar day
        starts at local midnight: reports, \"today\" totals, and daily invoice numbering
        all follow that day boundary. Earlier sales stay in the database unchanged.
        """

        # Calculate totals
        totals = self.calculate_cart_total(cart_items)

        cashier = (payment_info.get("cashier_name") or "").strip() or None
        sale_id: int
        changed_product_ids: set[int] = set()
        sale_at = _local_sale_timestamp()

        if db.connection is None:
            db.connect()
        conn = db.connection
        max_attempts = 5
        for attempt in range(max_attempts):
            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            try:
                invoice = self._generate_invoice_number_in_tx(cur)
                cur.execute(
                    """
                    INSERT INTO sales (
                        invoice_number, sale_date, subtotal, discount_amount, tax_amount,
                        total_amount, subtotal_cents, discount_amount_cents, tax_amount_cents,
                        total_amount_cents, payment_method, customer_name, cashier_name
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invoice,
                        sale_at,
                        totals["subtotal"],
                        totals["discount_amount"],
                        totals["tax_amount"],
                        totals["total"],
                        totals["subtotal_cents"],
                        totals["discount_amount_cents"],
                        totals["tax_amount_cents"],
                        totals["total_cents"],
                        payment_info.get("method", "CASH"),
                        payment_info.get("customer_name", ""),
                        cashier,
                    ),
                )
                sale_id = int(cur.lastrowid)

                for item in cart_items:
                    cur.execute(
                        """
                        INSERT INTO sale_items (
                            sale_id, product_id, quantity, unit_price, total, unit_price_cents, total_cents
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sale_id,
                            item["product_id"],
                            item["quantity"],
                            item["unit_price"],
                            item["total"],
                            to_cents(item["unit_price"]),
                            to_cents(item["total"]),
                        ),
                    )

                    cur.execute(
                        """
                        UPDATE products SET quantity_in_stock = quantity_in_stock - ? WHERE id = ?
                        """,
                        (item["quantity"], item["product_id"]),
                    )
                    changed_product_ids.add(int(item["product_id"]))

                conn.commit()
                break
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                if self._is_unique_number_conflict(exc, "sales.invoice_number") and attempt < (
                    max_attempts - 1
                ):
                    continue
                log_exception("Failed to record sale (integrity error)", invoice=locals().get("invoice"))
                raise
            except Exception:
                conn.rollback()
                log_exception("Failed to record sale")
                raise

        # Log for sync
        self.sync.log_change("sales", sale_id, SyncOperation.CREATE)
        for pid in changed_product_ids:
            self.sync.log_change("products", pid, SyncOperation.UPDATE)
            self.audit.record(
                event_type="stock_changed",
                entity_type="product",
                entity_id=pid,
                details={"reason": "sale_posted", "sale_id": sale_id},
            )
        self.audit.record(
            event_type="sale_recorded",
            entity_type="sale",
            entity_id=sale_id,
            details={"invoice_number": invoice, "total_cents": totals["total_cents"]},
        )

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

        ref_row = db.fetchone(
            """
            SELECT COALESCE(SUM(total_refund_amount_cents), 0) AS t
            FROM sale_returns
            WHERE sale_id = ?
            """,
            (sale_id,),
        )
        refund_total = cents_to_float(int(ref_row["t"] or 0)) if ref_row else 0.0
        sale_dict["refund_total"] = refund_total
        memo_rows = db.fetchall(
            """
            SELECT credit_memo_number, total_refund_amount, return_date
            FROM sale_returns
            WHERE sale_id = ?
            ORDER BY datetime(return_date), id
            """,
            (sale_id,),
        )
        sale_dict["refund_memos"] = [dict(m) for m in memo_rows]

        return sale_dict

    def find_sale_by_invoice(self, raw: str) -> dict | None:
        """Load a sale by invoice number (case-insensitive trim), or ``None``."""
        inv = (raw or "").strip()
        if not inv:
            return None
        row = db.fetchone(
            """
            SELECT id FROM sales
            WHERE UPPER(TRIM(invoice_number)) = UPPER(TRIM(?))
            LIMIT 1
            """,
            (inv,),
        )
        if not row:
            return None
        return self.get_sale(int(row["id"]))

    def returned_qty_by_sale_item(self, sale_id: int) -> dict[int, float]:
        """Map ``sale_items.id`` → cumulative quantity already returned for this sale."""
        rows = db.fetchall(
            """
            SELECT sri.sale_item_id AS sid, COALESCE(SUM(sri.quantity_returned), 0) AS q
            FROM sale_return_items sri
            JOIN sale_returns sr ON sr.id = sri.sale_return_id
            WHERE sr.sale_id = ?
            GROUP BY sri.sale_item_id
            """,
            (sale_id,),
        )
        return {int(r["sid"]): float(r["q"] or 0) for r in rows}

    def record_return(
        self,
        sale_id: int,
        lines: list[dict],
        payment_info: dict,
    ) -> dict:
        """
        Post a refund against an existing sale (does not delete the sale).

        Each line: ``sale_item_id`` (int), ``quantity`` (float > 0).
        Restores stock and inserts ``sale_returns`` / ``sale_return_items``.
        """
        if not lines:
            raise ValueError("Add at least one line to return.")

        sale = self.get_sale(sale_id)
        if not sale:
            raise ValueError("Sale not found.")

        returned_before = self.returned_qty_by_sale_item(sale_id)
        by_si = {int(it["id"]): dict(it) for it in sale.get("items") or []}

        prepared: list[tuple[int, int, float, float, float]] = []
        # (sale_item_id, product_id, qty, line_refund, orig_line_qty)

        for row in lines:
            si_id = int(row["sale_item_id"])
            qty = float(row["quantity"])
            if qty <= 0:
                raise ValueError("Return quantity must be greater than zero.")
            si = by_si.get(si_id)
            if not si:
                raise ValueError(f"Sale line #{si_id} is not on this invoice.")
            orig_q = float(si.get("quantity") or 0)
            if orig_q <= 0:
                raise ValueError(f"Invalid original quantity for line #{si_id}.")
            already = float(returned_before.get(si_id, 0.0))
            remaining = orig_q - already
            if qty > remaining + 1e-9:
                raise ValueError(
                    f"Cannot return {qty:g} of line #{si_id}; only {remaining:g} remaining."
                )
            line_total_cents = int(si.get("total_cents") or to_cents(si.get("total") or 0))
            unit_value_cents = decimal_money(line_total_cents) / decimal_money(orig_q)
            line_refund = cents_to_float(to_cents((unit_value_cents * decimal_money(qty)) / 100))
            pid = int(si["product_id"])
            prepared.append((si_id, pid, qty, line_refund, orig_q))

        total_refund_cents = sum(to_cents(p[3]) for p in prepared)
        total_refund = cents_to_float(total_refund_cents)
        if total_refund <= 0:
            raise ValueError("Refund total must be greater than zero.")

        method = (payment_info.get("method") or "CASH").strip() or "CASH"
        notes = (payment_info.get("notes") or "").strip() or None
        cashier = (payment_info.get("cashier_name") or "").strip() or None
        at = _local_sale_timestamp()

        if db.connection is None:
            db.connect()
        conn = db.connection
        return_id: int
        max_attempts = 5
        for attempt in range(max_attempts):
            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            try:
                memo = self._generate_credit_memo_number_in_tx(cur)
                cur.execute(
                    """
                    INSERT INTO sale_returns (
                        sale_id, credit_memo_number, return_date, total_refund_amount,
                        total_refund_amount_cents, payment_method, notes, cashier_name
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (sale_id, memo, at, total_refund, total_refund_cents, method, notes, cashier),
                )
                return_id = int(cur.lastrowid)

                for si_id, pid, qty, line_refund, _orig_q in prepared:
                    cur.execute(
                        """
                        INSERT INTO sale_return_items (
                            sale_return_id, sale_item_id, product_id, quantity_returned, line_refund_amount,
                            line_refund_amount_cents
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (return_id, si_id, pid, qty, line_refund, to_cents(line_refund)),
                    )
                    cur.execute(
                        """
                        UPDATE products
                        SET quantity_in_stock = quantity_in_stock + ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (qty, pid),
                    )

                conn.commit()
                break
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                if self._is_unique_number_conflict(
                    exc, "sale_returns.credit_memo_number"
                ) and attempt < (max_attempts - 1):
                    continue
                log_exception("Failed to record return (integrity error)", credit_memo=locals().get("memo"))
                raise
            except Exception:
                conn.rollback()
                log_exception("Failed to record return", sale_id=sale_id)
                raise

        self.sync.log_change("sale_returns", return_id, SyncOperation.CREATE)
        for _si_id, pid, _q, _lr, _oq in prepared:
            self.sync.log_change("products", pid, SyncOperation.UPDATE)
            self.audit.record(
                event_type="stock_changed",
                entity_type="product",
                entity_id=pid,
                details={"reason": "sale_refund", "sale_return_id": return_id},
            )
        self.audit.record(
            event_type="refund_recorded",
            entity_type="sale_return",
            entity_id=return_id,
            details={"sale_id": sale_id, "credit_memo_number": memo, "total_refund_cents": total_refund_cents},
        )

        return self.get_credit_memo(return_id)

    def get_credit_memo(self, return_id: int) -> dict | None:
        """Return header + lines + original invoice reference for printing."""
        hdr = db.fetchone(
            """
            SELECT sr.*, s.invoice_number AS original_invoice_number,
                   s.sale_date AS original_sale_date
            FROM sale_returns sr
            JOIN sales s ON s.id = sr.sale_id
            WHERE sr.id = ?
            """,
            (return_id,),
        )
        if not hdr:
            return None
        out = dict(hdr)
        items = db.fetchall(
            """
            SELECT sri.*, p.name, p.code
            FROM sale_return_items sri
            JOIN products p ON p.id = sri.product_id
            WHERE sri.sale_return_id = ?
            ORDER BY sri.id
            """,
            (return_id,),
        )
        out["items"] = [dict(x) for x in items]
        return out

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

    def refunds_total_for_range(self, start_date: str, end_date: str) -> float:
        """Sum of refund amounts with ``DATE(return_date)`` in inclusive range."""
        row = db.fetchone(
            """
            SELECT COALESCE(SUM(total_refund_amount_cents), 0) AS r
            FROM sale_returns
            WHERE DATE(return_date) BETWEEN ? AND ?
            """,
            (start_date, end_date),
        )
        if not row:
            return 0.0
        return cents_to_float(int(row["r"] or 0))

    def aggregate_sales_range(self, start_date: str, end_date: str) -> dict:
        """Invoice count, sales total, refunds, and net (sales − refunds) for the sales date range."""
        rows = self.get_sales_by_date(start_date, end_date)
        sales_sum_cents = sum(
            int(r.get("total_amount_cents") or to_cents(r.get("total_amount") or 0))
            for r in rows
        )
        refund_total = self.refunds_total_for_range(start_date, end_date)
        net_total = cents_to_float(sales_sum_cents - to_cents(refund_total))
        return {
            "invoice_count": len(rows),
            "sales_total": cents_to_float(sales_sum_cents),
            "refund_total": refund_total,
            "net_total": net_total,
            # Back-compat: ``gross_total`` was previously sum of sales; callers should use ``net_total`` for revenue.
            "gross_total": net_total,
        }

    def aggregate_sales_metrics_range(self, start_date: str, end_date: str) -> dict:
        """Single-row aggregates for receipt-style period summaries."""
        row = db.fetchone(
            """
            SELECT COUNT(*) AS invoice_count,
                   COALESCE(SUM(total_amount_cents), 0) AS sales_total_cents,
                   COALESCE(SUM(subtotal_cents), 0) AS subtotal_sum_cents,
                   COALESCE(SUM(discount_amount_cents), 0) AS discount_sum_cents
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            """,
            (start_date, end_date),
        )
        refund_total = self.refunds_total_for_range(start_date, end_date)
        if not row:
            return {
                "invoice_count": 0,
                "sales_total": 0.0,
                "subtotal_sum": 0.0,
                "discount_sum": 0.0,
                "refund_total": refund_total,
                "net_total": round(0.0 - refund_total, 2),
            }
        sales_total_cents = int(row["sales_total_cents"] or 0)
        sales_total = cents_to_float(sales_total_cents)
        net_total = cents_to_float(sales_total_cents - to_cents(refund_total))
        return {
            "invoice_count": int(row["invoice_count"] or 0),
            "sales_total": sales_total,
            "subtotal_sum": cents_to_float(int(row["subtotal_sum_cents"] or 0)),
            "discount_sum": cents_to_float(int(row["discount_sum_cents"] or 0)),
            "refund_total": refund_total,
            "net_total": net_total,
        }

    def daily_gross_by_date(self, start_date: str, end_date: str) -> list[tuple[str, float]]:
        """Each calendar day in range with **net** sales (sales − refunds that day)."""
        sales_rows = db.fetchall(
            """
            SELECT DATE(sale_date) AS d,
                   COALESCE(SUM(total_amount_cents), CAST(ROUND(COALESCE(SUM(total_amount), 0) * 100.0, 0) AS INTEGER)) AS g
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            GROUP BY DATE(sale_date)
            """,
            (start_date, end_date),
        )
        ref_rows = db.fetchall(
            """
            SELECT DATE(return_date) AS d,
                   COALESCE(SUM(total_refund_amount_cents), CAST(ROUND(COALESCE(SUM(total_refund_amount), 0) * 100.0, 0) AS INTEGER)) AS r
            FROM sale_returns
            WHERE DATE(return_date) BETWEEN ? AND ?
            GROUP BY DATE(return_date)
            """,
            (start_date, end_date),
        )
        by_sale = {str(r["d"]): int(r["g"] or 0) for r in sales_rows}
        by_ref = {str(r["d"]): int(r["r"] or 0) for r in ref_rows}
        cur = date.fromisoformat(start_date[:10])
        end = date.fromisoformat(end_date[:10])
        out: list[tuple[str, float]] = []
        while cur <= end:
            k = cur.isoformat()
            net = cents_to_float(by_sale.get(k, 0) - by_ref.get(k, 0))
            out.append((k, net))
            cur += timedelta(days=1)
        return out

    def hourly_gross_by_date(self, day_iso: str) -> list[tuple[str, float]]:
        """24 buckets (00–23) for one calendar day; **net** of sales and refunds in each hour."""
        day = day_iso[:10]
        s_rows = db.fetchall(
            """
            SELECT strftime('%H', sale_date) AS h,
                   COALESCE(SUM(total_amount_cents), CAST(ROUND(COALESCE(SUM(total_amount), 0) * 100.0, 0) AS INTEGER)) AS g
            FROM sales
            WHERE DATE(sale_date) = ?
            GROUP BY strftime('%H', sale_date)
            """,
            (day,),
        )
        r_rows = db.fetchall(
            """
            SELECT strftime('%H', return_date) AS h,
                   COALESCE(SUM(total_refund_amount_cents), CAST(ROUND(COALESCE(SUM(total_refund_amount), 0) * 100.0, 0) AS INTEGER)) AS r
            FROM sale_returns
            WHERE DATE(return_date) = ?
            GROUP BY strftime('%H', return_date)
            """,
            (day,),
        )
        by_s = {int(str(r["h"])): int(r["g"] or 0) for r in s_rows if r["h"] is not None}
        by_r = {int(str(r["h"])): int(r["r"] or 0) for r in r_rows if r["h"] is not None}
        return [
            (f"{day}T{h:02d}", cents_to_float(by_s.get(h, 0) - by_r.get(h, 0)))
            for h in range(24)
        ]

    def chart_series_for_overview(self, start_date: str, end_date: str) -> tuple[list[tuple[str, float]], str]:
        """
        Points for the dashboard bar chart:
        - single calendar day → hourly buckets;
        - 2–45 days → daily net per day;
        - longer ranges → one bar per calendar month (zero-filled).
        """
        sd = date.fromisoformat(start_date[:10])
        ed = date.fromisoformat(end_date[:10])
        n = (ed - sd).days + 1
        s, e = start_date[:10], end_date[:10]
        if n == 1:
            return self.hourly_gross_by_date(s), "Hourly net"
        if n <= 45:
            return self.daily_gross_by_date(s, e), "Daily net"
        s_rows = db.fetchall(
            """
            SELECT strftime('%Y-%m', sale_date) AS ym,
                   COALESCE(SUM(total_amount_cents), CAST(ROUND(COALESCE(SUM(total_amount), 0) * 100.0, 0) AS INTEGER)) AS g
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
            GROUP BY ym
            """,
            (s, e),
        )
        r_rows = db.fetchall(
            """
            SELECT strftime('%Y-%m', return_date) AS ym,
                   COALESCE(SUM(total_refund_amount_cents), CAST(ROUND(COALESCE(SUM(total_refund_amount), 0) * 100.0, 0) AS INTEGER)) AS r
            FROM sale_returns
            WHERE DATE(return_date) BETWEEN ? AND ?
            GROUP BY ym
            """,
            (s, e),
        )
        by_s = {str(r["ym"]): int(r["g"] or 0) for r in s_rows}
        by_r = {str(r["ym"]): int(r["r"] or 0) for r in r_rows}
        pts: list[tuple[str, float]] = []
        y, m = sd.year, sd.month
        while date(y, m, 1) <= ed:
            key = f"{y:04d}-{m:02d}"
            pts.append((key, cents_to_float(by_s.get(key, 0) - by_r.get(key, 0))))
            m += 1
            if m > 12:
                m = 1
                y += 1
        return pts, "Monthly net"

    def get_todays_totals(self) -> dict:
        """Aggregate today's sales for the dashboard (local SQLite)."""
        today = date.today().isoformat()
        return self.aggregate_sales_range(today, today)

    def cash_total_for_range(self, start_date: str, end_date: str) -> float:
        """Net cash: CASH sales minus CASH refunds in inclusive date range."""
        row_s = db.fetchone(
            """
            SELECT COALESCE(SUM(total_amount_cents), CAST(ROUND(COALESCE(SUM(total_amount), 0) * 100.0, 0) AS INTEGER)) AS s
            FROM sales
            WHERE DATE(sale_date) BETWEEN ? AND ?
              AND UPPER(TRIM(COALESCE(payment_method, ''))) = 'CASH'
            """,
            (start_date, end_date),
        )
        row_r = db.fetchone(
            """
            SELECT COALESCE(SUM(total_refund_amount_cents), CAST(ROUND(COALESCE(SUM(total_refund_amount), 0) * 100.0, 0) AS INTEGER)) AS s
            FROM sale_returns
            WHERE DATE(return_date) BETWEEN ? AND ?
              AND UPPER(TRIM(COALESCE(payment_method, ''))) = 'CASH'
            """,
            (start_date, end_date),
        )
        sales_cash = int(row_s["s"] or 0) if row_s else 0
        ref_cash = int(row_r["s"] or 0) if row_r else 0
        return cents_to_float(sales_cash - ref_cash)

    def get_todays_cash_total(self) -> float:
        """Net cash for today (sales − refunds), CASH method only."""
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
        """Next invoice for **today (local date)** — sequence resets each calendar day at local midnight.

        Format ``INV-YYYY-MM-DD-NNNNN`` (older rows may use ``INVYYYYMMDD…`` from the global-id scheme).
        """
        today = date.today().isoformat()
        row = db.fetchone(
            """
            SELECT COUNT(*) AS n FROM sales
            WHERE DATE(sale_date) = ?
            """,
            (today,),
        )
        n = int(row[0] or 0) + 1
        return f"INV-{today}-{n:05d}"

    def _generate_credit_memo_number(self) -> str:
        """Next credit memo for **today** — ``CRT-YYYY-MM-DD-NNNNN``."""
        today = date.today().isoformat()
        row = db.fetchone(
            """
            SELECT COUNT(*) AS n FROM sale_returns
            WHERE DATE(return_date) = ?
            """,
            (today,),
        )
        n = int(row[0] or 0) + 1
        return f"CRT-{today}-{n:05d}"

    @staticmethod
    def _is_unique_number_conflict(exc: sqlite3.IntegrityError, key: str) -> bool:
        msg = str(exc).lower()
        return "unique constraint failed" in msg and key.lower() in msg

    @staticmethod
    def _generate_invoice_number_in_tx(cur) -> str:
        today = date.today().isoformat()
        cur.execute(
            """
            SELECT COUNT(*) AS n FROM sales
            WHERE DATE(sale_date) = ?
            """,
            (today,),
        )
        row = cur.fetchone()
        n = int(row[0] or 0) + 1
        return f"INV-{today}-{n:05d}"

    @staticmethod
    def _generate_credit_memo_number_in_tx(cur) -> str:
        today = date.today().isoformat()
        cur.execute(
            """
            SELECT COUNT(*) AS n FROM sale_returns
            WHERE DATE(return_date) = ?
            """,
            (today,),
        )
        row = cur.fetchone()
        n = int(row[0] or 0) + 1
        return f"CRT-{today}-{n:05d}"
