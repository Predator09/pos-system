from __future__ import annotations

import csv

from app.services.product_service import ProductService


def _norm_csv_key(k: str) -> str:
    return (k or "").strip().lower().replace(" ", "_")


def _csv_row_to_payload(row: dict) -> dict:
    m = {_norm_csv_key(k): (v or "").strip() if isinstance(v, str) else v for k, v in row.items()}
    if "code" not in m and m.get("sku"):
        m["code"] = m["sku"]
    return m


class ProductsPresenter:
    """Business orchestration for the products UI."""

    def __init__(self, service: ProductService | None = None):
        self._svc = service or ProductService()

    @property
    def service(self) -> ProductService:
        return self._svc

    def refresh_data(self) -> tuple[list[dict], dict, list[str]]:
        products = self._svc.list_all_products()
        stats = self._svc.get_inventory_dashboard_stats()
        categories = self._svc.list_categories()
        return products, stats, categories

    @staticmethod
    def parse_opt_float(raw: str) -> float | None:
        t = str(raw).strip().replace(",", "")
        if not t:
            return None
        try:
            return float(t)
        except ValueError:
            return None

    def passes_filters(self, p: dict, criteria: dict) -> bool:
        q = (criteria.get("search") or "").strip().lower()
        bc = (p.get("barcode") or "").lower()
        if q and q not in (p.get("name") or "").lower() and q not in (p.get("code") or "").lower() and q not in bc:
            return False
        cat = criteria.get("category") or "(all)"
        if cat != "(all)" and (p.get("category") or "") != cat:
            return False

        pmin = self.parse_opt_float(criteria.get("price_min") or "")
        pmax = self.parse_opt_float(criteria.get("price_max") or "")
        price = float(p.get("selling_price") or 0)
        if pmin is not None and price < pmin:
            return False
        if pmax is not None and price > pmax:
            return False

        st = ProductService.row_status(p)
        fs = criteria.get("status") or "(all)"
        if fs != "(all)" and st != fs:
            return False

        sk = criteria.get("stock") or "(all)"
        if sk != "(all)":
            qty = float(p.get("quantity_in_stock") or 0)
            mn = float(p.get("minimum_stock_level") or 0)
            active = bool(p.get("is_active"))
            if sk == "low" and (not active or qty <= 0 or qty > mn):
                return False
            if sk == "out" and (not active or qty > 0):
                return False
            if sk == "ok" and (not active or qty <= 0 or qty <= mn):
                return False
        return True

    def bulk_deactivate(self, ids: list[int]) -> None:
        self._svc.bulk_deactivate(ids)

    def bulk_restock(self, ids: list[int], n: float) -> None:
        self._svc.bulk_add_stock(ids, n)

    def bulk_price_pct(self, ids: list[int], pct: float) -> None:
        self._svc.bulk_adjust_selling_price_percent(ids, pct)

    def bulk_min_alert(self, ids: list[int], minimum: float) -> None:
        self._svc.bulk_set_minimum_stock(ids, minimum)

    def export_csv(self, path: str, rows: list[dict], fields: list[str]) -> None:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for p in rows:
                w.writerow(
                    {
                        "id": p.get("id"),
                        "code": p.get("code"),
                        "barcode": p.get("barcode") or "",
                        "name": p.get("name"),
                        "category": p.get("category") or "",
                        "cost_price": p.get("cost_price"),
                        "selling_price": p.get("selling_price"),
                        "quantity_in_stock": p.get("quantity_in_stock"),
                        "minimum_stock_level": p.get("minimum_stock_level"),
                        "is_active": 1 if p.get("is_active") else 0,
                        "expiry_date": p.get("expiry_date") or "",
                        "image_path": p.get("image_path") or "",
                        "description": p.get("description") or "",
                    }
                )

    def import_csv(self, path: str) -> tuple[int, int, int]:
        n_ins = n_up = n_err = 0
        with open(path, newline="", encoding="utf-8-sig") as f:
            r = csv.DictReader(f)
            if not r.fieldnames:
                raise ValueError("CSV has no header row.")
            for raw in r:
                payload = _csv_row_to_payload(raw)
                try:
                    kind, _ = self._svc.upsert_product_from_row(payload)
                    if kind == "insert":
                        n_ins += 1
                    else:
                        n_up += 1
                except Exception:
                    n_err += 1
        return n_ins, n_up, n_err
