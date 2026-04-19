"""Stock receiving (goods receipt notes) — inventory increases with audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.database.connection import db
from app.database.sync import SyncOperation, SyncTracker
from app.services.app_logging import log_exception
from app.services.audit_service import AuditService


class PurchaseService:
    """Record supplier receipts: header (GRN) + lines; update on-hand qty and weighted-average cost."""

    def __init__(self):
        self.sync = SyncTracker(db)
        self.audit = AuditService()

    @staticmethod
    def _generate_reference() -> str:
        return f"GRN-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    def receive_receipt(
        self,
        lines: list[dict],
        *,
        supplier_name: str | None = None,
        supplier_phone: str | None = None,
        supplier_email: str | None = None,
        supplier_id: int | None = None,
        notes: str | None = None,
        update_average_cost: bool = True,
    ) -> dict:
        """
        Post one goods receipt.

        Each line: ``product_id`` (int), ``quantity`` (float > 0), ``unit_cost`` (float >= 0).

        Increments ``quantity_in_stock``. When ``update_average_cost`` is True, sets product
        ``cost_price`` to a **weighted moving average** of existing stock and this receipt.
        """
        if not lines:
            raise ValueError("Add at least one line item.")
        cleaned: list[tuple[int, float, float]] = []
        for row in lines:
            pid = int(row["product_id"])
            qty = float(row["quantity"])
            uc = float(row["unit_cost"])
            if qty <= 0:
                raise ValueError("Quantity must be greater than zero.")
            if uc < 0:
                raise ValueError("Unit cost cannot be negative.")
            cleaned.append((pid, qty, uc))

        reference = self._generate_reference()
        sup = (supplier_name or "").strip() or None
        phone = (supplier_phone or "").strip() or None
        email = (supplier_email or "").strip() or None
        nts = (notes or "").strip() or None
        sid = int(supplier_id) if supplier_id is not None else None
        if sid is not None and sid <= 0:
            sid = None

        if db.connection is None:
            db.connect()
        conn = db.connection
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        line_ids: list[int] = []
        try:
            cur.execute(
                """
                INSERT INTO purchase_receipts (
                    reference, supplier_name, notes, supplier_phone, supplier_email, supplier_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (reference, sup, nts, phone, email, sid),
            )
            receipt_id = cur.lastrowid

            for pid, qty, uc in cleaned:
                cur.execute("SELECT * FROM products WHERE id = ?", (pid,))
                prow = cur.fetchone()
                if not prow:
                    raise ValueError(f"Product #{pid} was not found.")
                p = dict(prow)
                if not p.get("is_active"):
                    raise ValueError(f"Product #{pid} is inactive — activate it before receiving stock.")

                old_qty = float(p.get("quantity_in_stock") or 0)
                old_cost = float(p.get("cost_price") or 0)
                new_qty = old_qty + qty
                if update_average_cost and new_qty > 0:
                    new_cost = (old_qty * old_cost + qty * uc) / new_qty
                else:
                    new_cost = old_cost

                cur.execute(
                    """
                    INSERT INTO purchases (product_id, quantity, cost_price, supplier_name, notes, receipt_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (pid, qty, uc, sup, None, receipt_id),
                )
                line_ids.append(cur.lastrowid)

                cur.execute(
                    """
                    UPDATE products
                    SET quantity_in_stock = ?, cost_price = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (new_qty, round(float(new_cost), 4), pid),
                )

            conn.commit()
        except Exception:
            conn.rollback()
            log_exception("Failed to receive purchase receipt", reference=reference)
            raise

        total_value = sum(q * c for _pid, q, c in cleaned)
        self.sync.log_change("purchase_receipts", receipt_id, SyncOperation.CREATE)
        for lid in line_ids:
            self.sync.log_change("purchases", lid, SyncOperation.CREATE)
        for pid in {p for p, _q, _c in cleaned}:
            self.sync.log_change("products", pid, SyncOperation.UPDATE)
            self.audit.record(
                event_type="stock_changed",
                entity_type="product",
                entity_id=pid,
                details={"reason": "purchase_receipt", "receipt_id": receipt_id},
            )
        self.audit.record(
            event_type="purchase_receipt_recorded",
            entity_type="purchase_receipt",
            entity_id=receipt_id,
            details={"reference": reference, "line_count": len(line_ids), "total_value": round(total_value, 2)},
        )

        return {
            "receipt_id": receipt_id,
            "reference": reference,
            "line_ids": line_ids,
            "line_count": len(line_ids),
            "total_value": round(total_value, 2),
        }

    def list_recent_receipts(self, limit: int = 50) -> list[dict]:
        rows = db.fetchall(
            """
            SELECT r.*,
              (SELECT COUNT(*) FROM purchases p WHERE p.receipt_id = r.id) AS line_count,
              (SELECT COALESCE(SUM(p.quantity * p.cost_price), 0)
                 FROM purchases p WHERE p.receipt_id = r.id) AS total_value
            FROM purchase_receipts r
            ORDER BY r.received_at DESC, r.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in rows]

    def get_receipt(self, receipt_id: int) -> dict | None:
        """Header row for one goods receipt, with line_count and total_value (same shape as list_recent_receipts)."""
        row = db.fetchone(
            """
            SELECT r.*,
              (SELECT COUNT(*) FROM purchases p WHERE p.receipt_id = r.id) AS line_count,
              (SELECT COALESCE(SUM(p.quantity * p.cost_price), 0)
                 FROM purchases p WHERE p.receipt_id = r.id) AS total_value
            FROM purchase_receipts r
            WHERE r.id = ?
            """,
            (receipt_id,),
        )
        return dict(row) if row else None

    def get_receipt_lines(self, receipt_id: int) -> list[dict]:
        rows = db.fetchall(
            """
            SELECT pu.*, prod.code AS product_code, prod.name AS product_name
            FROM purchases pu
            JOIN products prod ON prod.id = pu.product_id
            WHERE pu.receipt_id = ?
            ORDER BY pu.id
            """,
            (receipt_id,),
        )
        return [dict(r) for r in rows]

    def list_purchase_lines_history(self, limit: int = 200) -> list[dict]:
        rows = db.fetchall(
            """
            SELECT pu.id, pu.product_id, pu.quantity, pu.cost_price, pu.supplier_name,
                   pu.notes, pu.purchase_date, pu.created_at, pu.receipt_id,
                   prod.code AS product_code, prod.name AS product_name,
                   rc.reference AS receipt_reference
            FROM purchases pu
            JOIN products prod ON prod.id = pu.product_id
            LEFT JOIN purchase_receipts rc ON rc.id = pu.receipt_id
            ORDER BY datetime(COALESCE(pu.purchase_date, pu.created_at)) DESC, pu.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in rows]
