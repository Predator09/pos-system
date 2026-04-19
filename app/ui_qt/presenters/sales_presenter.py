from __future__ import annotations

from app.services.parked_sales_service import ParkedSalesService
from app.services.product_service import ProductService
from app.services.sales_service import SalesService


class SalesPresenter:
    """Business orchestration for POS workflows (non-UI)."""

    def __init__(
        self,
        sales_service: SalesService | None = None,
        product_service: ProductService | None = None,
        parked_service: ParkedSalesService | None = None,
    ):
        self._sales = sales_service or SalesService()
        self._products = product_service or ProductService()
        self._parked = parked_service or ParkedSalesService()

    @property
    def sales_service(self) -> SalesService:
        return self._sales

    @property
    def product_service(self) -> ProductService:
        return self._products

    @property
    def parked_service(self) -> ParkedSalesService:
        return self._parked

    def resolve_product(self, query: str):
        q = (query or "").strip()
        if not q:
            return None
        by_code = self._products.get_product_by_code(q)
        if by_code:
            return by_code
        by_bc = self._products.get_product_by_barcode(q)
        if by_bc:
            return by_bc
        if len(q) < 2:
            return []
        return self._products.search_products(q)

    @staticmethod
    def line_total(item: dict) -> float:
        gross = float(item["quantity"]) * float(item["unit_price"])
        disc = float(item.get("discount_amount") or 0)
        return round(max(0.0, gross - disc), 2)

    def qty_in_cart_for(self, cart: list[dict], product_id: int) -> float:
        return sum(float(it["quantity"]) for it in cart if int(it["product_id"]) == int(product_id))

    def is_sellable(self, product: dict) -> bool:
        return bool(product and product.get("is_active"))

    def stock_available(self, cart: list[dict], product: dict, add_qty: float) -> tuple[bool, str]:
        pid = int(product["id"])
        have = float(product.get("quantity_in_stock") or 0)
        in_cart = self.qty_in_cart_for(cart, pid)
        if in_cart + add_qty <= have + 1e-9:
            return True, ""
        msg = (
            f"Not enough stock for {product.get('name', '')}. "
            f"On hand: {have:g}, already in cart: {in_cart:g}, adding: {add_qty:g}."
        )
        return False, msg

    def line_qty_stock_ok(
        self, cart: list[dict], product_id: int, current_line_qty: float, new_line_qty: float
    ) -> tuple[bool, str]:
        p = self._products.get_product(product_id)
        if not p:
            return True, ""
        have = float(p.get("quantity_in_stock") or 0)
        in_other = self.qty_in_cart_for(cart, product_id) - float(current_line_qty)
        need = in_other + float(new_line_qty)
        if need <= have + 1e-9:
            return True, ""
        return False, f"Not enough stock for {p.get('name', '')}. On hand: {have:g}, need: {need:g}."

    def calculate_cart_total(self, cart: list[dict]) -> dict:
        return self._sales.calculate_cart_total(cart)
