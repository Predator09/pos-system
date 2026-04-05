"""Persist POS parked (held) carts in SQLite."""

from __future__ import annotations

import json
from datetime import datetime

from app.config import CURRENCY_SYMBOL
from app.database.connection import db
from app.services.sales_service import SalesService

MAX_PARKED_TICKETS = 20


def _money(amount: float) -> str:
    return f"{CURRENCY_SYMBOL} {float(amount):,.2f}"


class ParkedSalesService:
    """FIFO parked tickets; capped at ``MAX_PARKED_TICKETS``."""

    def __init__(self):
        self._sales = SalesService()

    def count(self) -> int:
        row = db.fetchone("SELECT COUNT(*) AS n FROM parked_sales")
        return int(row["n"]) if row else 0

    def list_tickets(self) -> list[dict]:
        rows = db.fetchall("SELECT * FROM parked_sales ORDER BY id ASC")
        tickets: list[dict] = []
        for row in rows:
            r = dict(row)
            try:
                cart = json.loads(r["cart_json"])
            except (json.JSONDecodeError, TypeError):
                cart = []
            if not isinstance(cart, list):
                cart = []
            totals = self._sales.calculate_cart_total(cart)
            tid = str(r["ticket_ref"] or "")
            at = str(r["created_at"] or "")
            hm = at[11:16] if len(at) >= 16 else at
            tickets.append(
                {
                    "db_id": int(r["id"]),
                    "id": tid,
                    "at": at,
                    "cart": cart,
                    "customer": r.get("customer") or "",
                    "payment": r.get("payment") or "CASH",
                    "tender": r.get("tender") or "",
                    "summary": f"{tid} · {hm} · {len(cart)} lines · {_money(totals['total'])}",
                }
            )
        return tickets

    def insert(self, ticket_ref: str, cart: list, customer: str, payment: str, tender: str) -> int:
        if self.count() >= MAX_PARKED_TICKETS:
            raise ValueError(
                f"Maximum {MAX_PARKED_TICKETS} parked tickets. Recall or complete one first."
            )
        created_at = datetime.now().isoformat(timespec="seconds")
        payload = json.dumps(cart, separators=(",", ":"))
        cur = db.execute(
            """
            INSERT INTO parked_sales (ticket_ref, created_at, customer, payment, tender, cart_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_ref,
                created_at,
                customer or "",
                payment or "CASH",
                tender or "",
                payload,
            ),
        )
        return int(cur.lastrowid)

    def delete(self, row_id: int) -> None:
        db.execute("DELETE FROM parked_sales WHERE id = ?", (int(row_id),))
