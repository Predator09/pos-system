from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from app.database.connection import db
from app.database.sync import SyncOperation, SyncTracker


def _product_image_dir() -> Path:
    from app.services.shop_context import product_images_dir

    return product_images_dir()

_UPDATABLE_FIELDS = frozenset(
    {
        "name",
        "code",
        "category",
        "description",
        "cost_price",
        "selling_price",
        "minimum_stock_level",
        "quantity_in_stock",
        "is_active",
        "expiry_date",
        "image_path",
    }
)


class ProductService:
    def __init__(self):
        self.sync = SyncTracker(db)

    def list_products(self):
        """Active products only (POS / picker)."""
        results = db.fetchall("SELECT * FROM products WHERE is_active = 1 ORDER BY name")
        return [dict(row) for row in results]

    def list_all_products(self):
        """Full catalog for inventory screen."""
        results = db.fetchall("SELECT * FROM products ORDER BY name COLLATE NOCASE")
        return [dict(row) for row in results]

    def list_categories(self) -> list[str]:
        rows = db.fetchall(
            """
            SELECT DISTINCT category FROM products
            WHERE category IS NOT NULL AND TRIM(category) != ''
            ORDER BY category COLLATE NOCASE
            """
        )
        return [str(r[0]) for r in rows]

    def get_product(self, product_id: int):
        result = db.fetchone("SELECT * FROM products WHERE id = ?", (product_id,))
        return dict(result) if result else None

    def get_product_by_code(self, code: str):
        result = db.fetchone("SELECT * FROM products WHERE code = ?", (code,))
        return dict(result) if result else None

    def search_products(self, query: str):
        query_param = f"%{query}%"
        results = db.fetchall(
            """
            SELECT * FROM products
            WHERE is_active = 1 AND (name LIKE ? OR code LIKE ?)
            ORDER BY name
            """,
            (query_param, query_param),
        )
        return [dict(row) for row in results]

    def list_active_products_by_units_sold(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """
        Active catalog for gallery / best-sellers: ordered by **lifetime units sold**
        (``sale_items``), then name. Each row includes ``units_sold`` (float).
        """
        where = ["p.is_active = 1"]
        params: list = []
        cat = (category or "").strip()
        if cat and cat != "(all)":
            where.append("TRIM(COALESCE(p.category, '')) = ?")
            params.append(cat)
        q = (search or "").strip()
        if q:
            qq = f"%{q.lower()}%"
            where.append("(LOWER(p.name) LIKE ? OR LOWER(p.code) LIKE ?)")
            params.extend([qq, qq])
        wh = " AND ".join(where)
        lim = max(1, min(int(limit), 500))
        params.append(lim)
        rows = db.fetchall(
            f"""
            SELECT p.*,
                   COALESCE(SUM(si.quantity), 0) AS units_sold
            FROM products p
            LEFT JOIN sale_items si ON si.product_id = p.id
            WHERE {wh}
            GROUP BY p.id
            ORDER BY units_sold DESC, p.name COLLATE NOCASE
            LIMIT ?
            """,
            tuple(params),
        )
        return [dict(row) for row in rows]

    def get_inventory_dashboard_stats(self) -> dict:
        total = db.fetchone("SELECT COUNT(*) AS n FROM products")
        low = db.fetchone(
            """
            SELECT COUNT(*) AS n FROM products
            WHERE is_active = 1 AND quantity_in_stock > 0
              AND quantity_in_stock <= minimum_stock_level
            """
        )
        out = db.fetchone(
            """
            SELECT COUNT(*) AS n FROM products
            WHERE is_active = 1 AND quantity_in_stock <= 0
            """
        )
        val = db.fetchone(
            """
            SELECT COALESCE(SUM(selling_price * quantity_in_stock), 0) AS v
            FROM products WHERE is_active = 1
            """
        )
        avg = db.fetchone(
            """
            SELECT COALESCE(AVG(selling_price), 0) AS a
            FROM products WHERE is_active = 1
            """
        )
        top = db.fetchone(
            """
            SELECT TRIM(p.category) AS c, SUM(si.quantity) AS q
            FROM sale_items si
            JOIN products p ON p.id = si.product_id
            WHERE p.category IS NOT NULL AND TRIM(p.category) != ''
            GROUP BY TRIM(p.category)
            ORDER BY q DESC
            LIMIT 1
            """
        )
        return {
            "total_products": int(total["n"] or 0) if total else 0,
            "low_stock": int(low["n"] or 0) if low else 0,
            "out_of_stock": int(out["n"] or 0) if out else 0,
            "inventory_value": float(val["v"] or 0) if val else 0.0,
            "top_category": str(top["c"]) if top and top["c"] else None,
            "avg_price": float(avg["a"] or 0) if avg else 0.0,
        }

    def create_product(
        self,
        name: str,
        code: str,
        cost_price: float,
        selling_price: float,
        **kwargs,
    ):
        cursor = db.execute(
            """
            INSERT INTO products (
                name, code, cost_price, selling_price, category, description,
                quantity_in_stock, minimum_stock_level, is_active,
                expiry_date, image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                code,
                cost_price,
                selling_price,
                kwargs.get("category"),
                kwargs.get("description"),
                float(kwargs.get("quantity_in_stock") or 0),
                float(kwargs.get("minimum_stock_level") if kwargs.get("minimum_stock_level") is not None else 10),
                1 if kwargs.get("is_active", True) else 0,
                kwargs.get("expiry_date") or None,
                kwargs.get("image_path") or None,
            ),
        )
        product_id = cursor.lastrowid
        self.sync.log_change("products", product_id, SyncOperation.CREATE)
        return self.get_product(product_id)

    def update_product(self, product_id: int, **kwargs):
        product = self.get_product(product_id)
        if not product:
            return None
        updates = []
        params = []
        for key, value in kwargs.items():
            if key not in _UPDATABLE_FIELDS:
                continue
            updates.append(f"{key} = ?")
            params.append(value)
        if not updates:
            return product
        params.append(product_id)
        query = f"UPDATE products SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        db.execute(query, tuple(params))
        self.sync.log_change("products", product_id, SyncOperation.UPDATE)
        return self.get_product(product_id)

    def set_product_image_from_file(self, product_id: int, source_path: str) -> str:
        """Copy image into ``data/product_images`` and set ``products.image_path``."""
        if not self.get_product(product_id):
            raise ValueError("Product not found")
        src = Path(source_path)
        if not src.is_file():
            raise ValueError("File not found")
        ext = src.suffix.lower() if src.suffix else ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
            ext = ".jpg"
        img_dir = _product_image_dir()
        img_dir.mkdir(parents=True, exist_ok=True)
        pid = int(product_id)
        for old in img_dir.glob(f"product_{pid}.*"):
            try:
                old.unlink()
            except OSError:
                pass
        dest = img_dir / f"product_{pid}{ext}"
        shutil.copy2(src, dest)
        new_path = str(dest.resolve())
        self.update_product(product_id, image_path=new_path)
        return new_path

    def adjust_stock_delta(self, product_id: int, delta: float):
        p = self.get_product(product_id)
        if not p:
            return None
        cur = float(p.get("quantity_in_stock") or 0)
        new_qty = max(0.0, cur + float(delta))
        db.execute(
            """
            UPDATE products SET quantity_in_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """,
            (new_qty, product_id),
        )
        self.sync.log_change("products", product_id, SyncOperation.UPDATE)
        return self.get_product(product_id)

    def get_low_stock(self):
        results = db.fetchall(
            """
            SELECT * FROM products
            WHERE is_active = 1 AND quantity_in_stock <= minimum_stock_level
            ORDER BY quantity_in_stock ASC
            """
        )
        return [dict(row) for row in results]

    def update_stock(self, product_id: int, quantity: float):
        db.execute(
            """
            UPDATE products SET quantity_in_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """,
            (quantity, product_id),
        )
        self.sync.log_change("products", product_id, SyncOperation.UPDATE)

    def bulk_deactivate(self, product_ids: list[int]):
        if not product_ids:
            return 0
        placeholders = ",".join("?" * len(product_ids))
        db.execute(
            f"""
            UPDATE products SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
            """,
            tuple(product_ids),
        )
        for pid in product_ids:
            self.sync.log_change("products", pid, SyncOperation.UPDATE)
        return len(product_ids)

    def bulk_add_stock(self, product_ids: list[int], delta: float):
        if not product_ids:
            return 0
        n = 0
        for pid in product_ids:
            if self.adjust_stock_delta(pid, delta):
                n += 1
        return n

    def bulk_set_minimum_stock(self, product_ids: list[int], minimum: float):
        if not product_ids:
            return 0
        placeholders = ",".join("?" * len(product_ids))
        params = [float(minimum)] + list(product_ids)
        db.execute(
            f"""
            UPDATE products SET minimum_stock_level = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
            """,
            tuple(params),
        )
        for pid in product_ids:
            self.sync.log_change("products", pid, SyncOperation.UPDATE)
        return len(product_ids)

    def bulk_adjust_selling_price_percent(self, product_ids: list[int], percent: float):
        """percent=10 means +10%% to selling_price."""
        if not product_ids:
            return 0
        factor = 1.0 + float(percent) / 100.0
        placeholders = ",".join("?" * len(product_ids))
        params = [factor] + list(product_ids)
        db.execute(
            f"""
            UPDATE products SET selling_price = ROUND(selling_price * ?, 2),
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
            """,
            tuple(params),
        )
        for pid in product_ids:
            self.sync.log_change("products", pid, SyncOperation.UPDATE)
        return len(product_ids)

    def upsert_product_from_row(self, row: dict) -> tuple[str, int]:
        """Import: match by code. Returns ('insert'|'update', id)."""
        code = (row.get("code") or "").strip()
        if not code:
            raise ValueError("missing code")
        name = (row.get("name") or "").strip() or code
        cost = float(row.get("cost_price") or 0)
        sell = float(row.get("selling_price") or 0)
        active_raw = str(row.get("is_active", "1")).strip().lower()
        is_active = active_raw in ("1", "true", "yes", "y", "active")
        existing = self.get_product_by_code(code)
        common = dict(
            category=row.get("category") or None,
            description=row.get("description") or None,
            quantity_in_stock=float(row.get("quantity_in_stock") or 0),
            minimum_stock_level=float(
                row.get("minimum_stock_level") if row.get("minimum_stock_level") not in (None, "") else 10
            ),
            is_active=1 if is_active else 0,
            expiry_date=(row.get("expiry_date") or "").strip() or None,
            image_path=(row.get("image_path") or "").strip() or None,
        )
        if existing:
            pid = int(existing["id"])
            self.update_product(
                pid,
                name=name,
                cost_price=cost,
                selling_price=sell,
                **common,
            )
            return "update", pid
        p = self.create_product(
            name,
            code,
            cost,
            sell,
            category=common["category"],
            description=common["description"],
            quantity_in_stock=common["quantity_in_stock"],
            minimum_stock_level=common["minimum_stock_level"],
            is_active=is_active,
            expiry_date=common["expiry_date"],
            image_path=common["image_path"],
        )
        return "insert", int(p["id"])

    @staticmethod
    def row_status(product: dict) -> str:
        """active | inactive | expired (for display/filter). Expiry overrides inactive so past-date stock stays visually critical."""
        exp = (product.get("expiry_date") or "").strip()
        if exp and exp < date.today().isoformat():
            return "expired"
        if not product.get("is_active"):
            return "inactive"
        return "active"

    @staticmethod
    def inventory_row_tag(product: dict) -> str:
        """Row accent for inventory grids: ``expired`` | ``inactive`` | ``bad`` | ``low`` | ``active_ok``."""
        st = ProductService.row_status(product)
        if st == "expired":
            return "expired"
        if st == "inactive":
            return "inactive"
        qty = float(product.get("quantity_in_stock") or 0)
        if qty <= 0:
            return "bad"
        if qty <= float(product.get("minimum_stock_level") or 0):
            return "low"
        return "active_ok"
