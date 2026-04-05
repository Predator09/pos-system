"""Registered suppliers — saved for reuse on goods receipts (GRN)."""

from __future__ import annotations

from app.database.connection import db


class SupplierService:
    def list_active(self, *, limit: int = 500) -> list[dict]:
        rows = db.fetchall(
            """
            SELECT id, name, phone, email, address, notes, is_active, created_at, updated_at
            FROM suppliers
            WHERE is_active = 1
            ORDER BY lower(name), id
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in rows]

    def get(self, supplier_id: int) -> dict | None:
        row = db.fetchone(
            """
            SELECT id, name, phone, email, address, notes, is_active, created_at, updated_at
            FROM suppliers WHERE id = ?
            """,
            (int(supplier_id),),
        )
        return dict(row) if row else None

    def create(
        self,
        *,
        name: str,
        phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
        notes: str | None = None,
    ) -> int:
        n = (name or "").strip()
        if not n:
            raise ValueError("Supplier name is required.")
        if db.connection is None:
            db.connect()
        db.execute(
            """
            INSERT INTO suppliers (name, phone, email, address, notes, is_active, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """,
            (
                n,
                (phone or "").strip() or None,
                (email or "").strip() or None,
                (address or "").strip() or None,
                (notes or "").strip() or None,
            ),
        )
        row = db.fetchone("SELECT last_insert_rowid() AS id")
        return int(row["id"]) if row else 0

    def update(
        self,
        supplier_id: int,
        *,
        name: str,
        phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
        notes: str | None = None,
    ) -> None:
        n = (name or "").strip()
        if not n:
            raise ValueError("Supplier name is required.")
        db.execute(
            """
            UPDATE suppliers
            SET name = ?, phone = ?, email = ?, address = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                n,
                (phone or "").strip() or None,
                (email or "").strip() or None,
                (address or "").strip() or None,
                (notes or "").strip() or None,
                int(supplier_id),
            ),
        )

    def deactivate(self, supplier_id: int) -> None:
        db.execute(
            "UPDATE suppliers SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (int(supplier_id),),
        )
