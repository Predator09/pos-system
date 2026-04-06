"""Point of sale Qt view; same SalesService / ProductService / ParkedSalesService flows as Tk."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import PAD_MD
from app.services.parked_sales_service import MAX_PARKED_TICKETS, ParkedSalesService
from app.services.product_service import ProductService
from app.services.sales_service import SalesService, cashier_display_name

from app.ui_qt.dialogs_qt import PickProductDialogQt, ReceiptPreviewDialogQt, RecallParkedDialogQt
from app.ui_qt.helpers_qt import ask_yes_no, ask_yes_no_cancel, format_money, info_message, warning_message

_CART_COLS = ("code", "name", "qty", "price", "disc", "total")
# Compact empty cart; table grows with line count up to max, then scrolls.
_CART_TABLE_MIN_ROWS = 2
_CART_TABLE_MAX_ROWS = 18
_CART_TABLE_ROW_PX = 28


class SalesView(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._sales = SalesService()
        self._products = ProductService()
        self._parked_svc = ParkedSalesService()
        self.cart: list[dict] = []
        self._parked: list[dict] = []
        self._kpi_labels: dict[str, QLabel] = {}

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(PAD_MD)

        # --- Top: compact KPI row + clock (shell already shows page title) ---
        top_bar = QFrame()
        top_bar.setObjectName("card")
        top_row = QHBoxLayout(top_bar)
        top_row.setContentsMargins(12, 8, 12, 8)
        top_row.setSpacing(16)
        for key, title in (
            ("invoices", "Invoices"),
            ("gross", "Gross"),
            ("cash", "Cash"),
            ("lines", "Cart lines"),
            ("parked", "Parked"),
        ):
            cell = QVBoxLayout()
            cell.setSpacing(2)
            tl = QLabel(title)
            tl.setObjectName("muted")
            cell.addWidget(tl)
            lab = QLabel("—")
            lab.setObjectName("kpiValueSm")
            cell.addWidget(lab)
            top_row.addLayout(cell)
            self._kpi_labels[key] = lab
        top_row.addStretch(1)
        self._clock_lbl = QLabel("")
        self._clock_lbl.setObjectName("heroTime")
        top_row.addWidget(self._clock_lbl, alignment=Qt.AlignVCenter)
        root.addWidget(top_bar)

        # --- Main: register (left) + checkout (right) ---
        body = QHBoxLayout()
        body.setSpacing(PAD_MD)
        left_col = QVBoxLayout()
        left_col.setSpacing(PAD_MD)
        left_col.setContentsMargins(0, 0, 0, 0)

        scan_card = QFrame()
        scan_card.setObjectName("card")
        scan_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        reg = QVBoxLayout(scan_card)
        reg.setContentsMargins(16, 12, 16, 12)
        reg.setSpacing(8)
        scan_title = QLabel("Scan & add")
        scan_title.setObjectName("pageSubtitle")
        reg.addWidget(scan_title)

        er = QGridLayout()
        er.setHorizontalSpacing(12)
        er.setVerticalSpacing(6)
        l_qty = QLabel("Qty")
        l_qty.setObjectName("muted")
        l_lookup = QLabel("Lookup")
        l_lookup.setObjectName("muted")
        er.addWidget(l_qty, 0, 0, alignment=Qt.AlignBottom | Qt.AlignLeft)
        er.addWidget(l_lookup, 0, 1, alignment=Qt.AlignBottom | Qt.AlignLeft)
        self._qty_spin = QDoubleSpinBox()
        self._qty_spin.setMinimum(0.01)
        self._qty_spin.setMaximum(9999.0)
        self._qty_spin.setValue(1.0)
        self._qty_spin.setDecimals(2)
        self._qty_spin.setFixedWidth(88)
        self._qty_spin.setFixedHeight(36)
        er.addWidget(self._qty_spin, 1, 0, alignment=Qt.AlignTop)
        self._search = QLineEdit()
        self._search.setPlaceholderText("SKU, barcode scan, or name…")
        self._search.setFixedHeight(36)
        self._search.returnPressed.connect(self._on_add_product)
        er.addWidget(self._search, 1, 1, alignment=Qt.AlignTop)
        add_b = QPushButton("Add", clicked=self._on_add_product)
        add_b.setObjectName("primary")
        add_b.setCursor(Qt.PointingHandCursor)
        add_b.setFixedHeight(36)
        add_b.setMinimumWidth(76)
        br_b = QPushButton("Browse", clicked=self._pick_product)
        br_b.setCursor(Qt.PointingHandCursor)
        br_b.setFixedHeight(36)
        br_b.setMinimumWidth(88)
        er.addWidget(add_b, 1, 2, alignment=Qt.AlignTop)
        er.addWidget(br_b, 1, 3, alignment=Qt.AlignTop)
        er.setColumnStretch(1, 1)
        reg.addLayout(er)

        cust = QHBoxLayout()
        cust.setSpacing(8)
        lc = QLabel("Customer (optional)")
        lc.setObjectName("muted")
        cust.addWidget(lc)
        self._customer = QLineEdit()
        self._customer.setMinimumHeight(34)
        cust.addWidget(self._customer, 1)
        reg.addLayout(cust)
        left_col.addWidget(scan_card)

        cart_card = QFrame()
        cart_card.setObjectName("card")
        cart_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        cart_lay = QVBoxLayout(cart_card)
        cart_lay.setContentsMargins(16, 12, 16, 12)
        cart_lay.setSpacing(8)

        cart_title = QLabel("Line items")
        cart_title.setObjectName("pageSubtitle")
        cart_lay.addWidget(cart_title)

        self._cart_table = QTableWidget(0, len(_CART_COLS))
        self._cart_table.setHorizontalHeaderLabels(["Code", "Product", "Qty", "Price", "Disc", "Line"])
        self._cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._cart_table.setSelectionMode(QTableWidget.SingleSelection)
        self._cart_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._cart_table.verticalHeader().setVisible(False)
        self._cart_table.verticalHeader().setDefaultSectionSize(_CART_TABLE_ROW_PX)
        self._cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (0, 2, 3, 4, 5):
            self._cart_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self._cart_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cart_lay.addWidget(self._cart_table, 0)

        def _act_btn(text: str, fn, min_w: int = 88) -> QPushButton:
            b = QPushButton(text, clicked=fn)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(32)
            b.setMinimumWidth(min_w)
            return b

        act_row0 = QHBoxLayout()
        act_row0.setSpacing(8)
        line_tag = QLabel("Line")
        line_tag.setObjectName("muted")
        act_row0.addWidget(line_tag)
        act_row0.addWidget(_act_btn("Set qty", self._edit_line_qty))
        act_row0.addWidget(_act_btn("Discount", self._line_discount))
        act_row0.addWidget(_act_btn("Remove", self._remove_selected_line))
        act_row0.addStretch(1)
        cart_lay.addLayout(act_row0)

        act_row1 = QHBoxLayout()
        act_row1.setSpacing(8)
        tk_tag = QLabel("Ticket")
        tk_tag.setObjectName("muted")
        act_row1.addWidget(tk_tag)
        act_row1.addWidget(_act_btn("Park", self._park_sale))
        act_row1.addWidget(_act_btn("Recall", self._recall_parked))
        act_row1.addStretch(1)
        act_row1.addWidget(_act_btn("Clear cart", self._confirm_clear_cart, 100))
        cart_lay.addLayout(act_row1)

        left_col.addWidget(cart_card)
        left_col.addStretch(1)

        body.addLayout(left_col, stretch=3)

        pay_card = QFrame()
        pay_card.setObjectName("card")
        pay_card.setMinimumWidth(288)
        pay_card.setMaximumWidth(400)
        pay_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        checkout = QVBoxLayout(pay_card)
        checkout.setContentsMargins(16, 12, 16, 12)
        checkout.setSpacing(8)

        self._subtotal_lbl = QLabel()
        self._disc_lbl = QLabel()
        checkout.addWidget(self._subtotal_lbl)
        checkout.addWidget(self._disc_lbl)
        line_sep = QFrame()
        line_sep.setFrameShape(QFrame.Shape.HLine)
        line_sep.setFrameShadow(QFrame.Shadow.Sunken)
        checkout.addWidget(line_sep)
        tot_row = QHBoxLayout()
        tot_row.addWidget(QLabel("Total"))
        self._total_lbl = QLabel()
        self._total_lbl.setObjectName("kpiValue")
        tot_row.addStretch(1)
        tot_row.addWidget(self._total_lbl)
        checkout.addLayout(tot_row)

        pay_grid = QGridLayout()
        pay_grid.setHorizontalSpacing(8)
        pay_grid.setVerticalSpacing(4)
        self._pay_group = QButtonGroup(self)
        self._payment_var = "CASH"
        pay_opts = (("Cash", "CASH"), ("Card", "CARD"), ("Mobile", "MOBILE"), ("Check", "CHECK"))
        for i, (text, val) in enumerate(pay_opts):
            rb = QRadioButton(text)
            self._pay_group.addButton(rb)
            pay_grid.addWidget(rb, i // 2, i % 2)
            if val == "CASH":
                rb.setChecked(True)
            rb.toggled.connect(lambda c, v=val: self._on_payment_toggled(c, v))
        checkout.addLayout(pay_grid)

        self._tender_frame = QWidget()
        tlay = QVBoxLayout(self._tender_frame)
        tlay.setContentsMargins(0, 0, 0, 0)
        tlay.setSpacing(6)
        tlay.addWidget(QLabel("Amount received"))
        self._tender = QLineEdit()
        self._tender.setMinimumHeight(34)
        self._tender.textChanged.connect(self._update_tender_display)
        tlay.addWidget(self._tender)
        ch_row = QHBoxLayout()
        ch_row.addWidget(QLabel("Change"))
        ch_row.addStretch(1)
        self._change_lbl = QLabel()
        self._change_lbl.setObjectName("kpiValueSm")
        ch_row.addWidget(self._change_lbl)
        tlay.addLayout(ch_row)
        checkout.addWidget(self._tender_frame)

        comp = QPushButton("Complete sale", clicked=self._complete_sale)
        comp.setObjectName("primary")
        comp.setCursor(Qt.PointingHandCursor)
        comp.setMinimumHeight(44)
        checkout.addWidget(comp)
        new_c = QPushButton("New cart", clicked=self._confirm_clear_cart)
        new_c.setCursor(Qt.PointingHandCursor)
        new_c.setMinimumHeight(36)
        checkout.addWidget(new_c)

        body.addWidget(pay_card, stretch=1, alignment=Qt.AlignmentFlag.AlignTop)
        root.addLayout(body, stretch=1)

        self._on_payment_change()
        QTimer.singleShot(0, self._sync_cart_table_height)

    def _on_payment_toggled(self, checked: bool, val: str) -> None:
        if checked:
            self._payment_var = val
            self._on_payment_change()

    def _tick_clock(self) -> None:
        self._clock_lbl.setText(datetime.now().strftime("%H:%M:%S"))

    def _parse_qty(self) -> float:
        try:
            q = float(self._qty_spin.value())
            if q <= 0:
                raise ValueError
            return q
        except (TypeError, ValueError):
            return 0.0

    def _qty_in_cart_for(self, product_id: int) -> float:
        t = 0.0
        for it in self.cart:
            if it["product_id"] == product_id:
                t += float(it["quantity"])
        return t

    def _resolve_product(self, query: str):
        q = query.strip()
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

    def _ensure_sellable(self, p: dict) -> bool:
        if not p.get("is_active"):
            warning_message(self.window(), "POS", "This product is inactive.")
            return False
        return True

    def _role_can_override_stock(self) -> bool:
        u = getattr(self._main, "current_user", None) or {}
        return str(u.get("role") or "").lower() == "owner"

    def _offer_stock_override(self, title: str, body: str) -> bool:
        if not self._role_can_override_stock():
            return False
        return ask_yes_no(
            self.window(),
            title,
            body + "\n\nOwner override: allow this sale anyway?",
        )

    def _stock_available(self, p: dict, add_qty: float) -> bool:
        pid = int(p["id"])
        have = float(p.get("quantity_in_stock") or 0)
        in_cart = self._qty_in_cart_for(pid)
        if in_cart + add_qty <= have + 1e-9:
            return True
        detail = (
            f"Not enough stock for {p.get('name', '')}.\n"
            f"On hand: {have:g}, already in cart: {in_cart:g}, adding: {add_qty:g}."
        )
        if self._offer_stock_override("Stock", detail):
            return True
        warning_message(self.window(), "Stock", detail.replace("\n", " "))
        return False

    def _line_qty_stock_ok(self, product_id: int, current_line_qty: float, new_line_qty: float) -> bool:
        p = self._products.get_product(product_id)
        if not p:
            return True
        have = float(p.get("quantity_in_stock") or 0)
        in_other = self._qty_in_cart_for(product_id) - float(current_line_qty)
        need = in_other + float(new_line_qty)
        if need <= have + 1e-9:
            return True
        detail = (
            f"Not enough stock for {p.get('name', '')}.\n"
            f"On hand: {have:g}, need for this line: {need:g}."
        )
        if self._offer_stock_override("Stock", detail):
            return True
        warning_message(self.window(), "Stock", detail.replace("\n", " "))
        return False

    def _on_add_product(self) -> None:
        query = self._search.text()
        qty = self._parse_qty()
        if qty <= 0:
            warning_message(self.window(), "POS", "Enter a valid quantity (> 0).")
            return

        resolved = self._resolve_product(query)
        if resolved is None:
            return
        if isinstance(resolved, list):
            if not resolved:
                warning_message(self.window(), "POS", "No matching active products.")
                return
            if len(resolved) == 1:
                p = resolved[0]
            else:
                d = PickProductDialogQt(self.window(), self._products, products=resolved)
                if d.exec() != QDialog.DialogCode.Accepted or not d.result:
                    return
                p = d.result
        else:
            p = resolved

        if not self._ensure_sellable(p):
            return
        if not self._stock_available(p, qty):
            return

        self._add_line(
            int(p["id"]),
            p.get("code") or "",
            p.get("name") or "",
            float(p.get("selling_price") or 0),
            qty,
        )
        self._search.clear()
        self._qty_spin.setValue(1.0)
        self._search.setFocus()
        self._refresh_cart_tree()

    def _pick_product(self) -> None:
        d = PickProductDialogQt(self.window(), self._products)
        if d.exec() != QDialog.DialogCode.Accepted or not d.result:
            return
        p = d.result
        qty = self._parse_qty()
        if qty <= 0:
            qty = 1.0
        if not self._ensure_sellable(p):
            return
        if not self._stock_available(p, qty):
            return
        self._add_line(
            int(p["id"]),
            p.get("code") or "",
            p.get("name") or "",
            float(p.get("selling_price") or 0),
            qty,
        )
        self._refresh_cart_tree()

    @staticmethod
    def _line_total(item: dict) -> float:
        gross = float(item["quantity"]) * float(item["unit_price"])
        disc = float(item.get("discount_amount") or 0)
        return round(max(0.0, gross - disc), 2)

    def _add_line(self, product_id: int, code: str, name: str, unit_price: float, quantity: float) -> None:
        for it in self.cart:
            if it["product_id"] == product_id:
                it["quantity"] = float(it["quantity"]) + quantity
                it["total"] = self._line_total(it)
                self._refresh_cart_tree()
                self._update_totals()
                return
        self.cart.append(
            {
                "product_id": product_id,
                "code": code,
                "name": name,
                "unit_price": unit_price,
                "quantity": quantity,
                "discount_amount": 0.0,
                "total": 0.0,
            }
        )
        self.cart[-1]["total"] = self._line_total(self.cart[-1])
        self._refresh_cart_tree()
        self._update_totals()

    def add_to_cart_by_product_id(self, product_id: int, quantity: float = 1.0) -> None:
        q = float(quantity)
        if q <= 0:
            warning_message(self.window(), "POS", "Quantity must be greater than zero.")
            return
        p = self._products.get_product(int(product_id))
        if not p:
            warning_message(self.window(), "POS", "Product not found.")
            return
        if not self._ensure_sellable(p):
            return
        if not self._stock_available(p, q):
            return
        self._add_line(
            int(p["id"]),
            p.get("code") or "",
            p.get("name") or "",
            float(p.get("selling_price") or 0),
            q,
        )
        self._search.setFocus()

    def _selected_index(self) -> int | None:
        r = self._cart_table.currentRow()
        if r < 0 or r >= len(self.cart):
            return None
        return r

    def _edit_line_qty(self) -> None:
        idx = self._selected_index()
        if idx is None:
            warning_message(self.window(), "POS", "Select a cart line.")
            return
        it = self.cart[idx]
        v, ok = QInputDialog.getDouble(
            self.window(),
            "Quantity",
            f"New qty for {it.get('name', '')}:",
            float(it["quantity"]),
            0.0,
            1_000_000.0,
            3,
        )
        if not ok:
            return
        if v <= 0:
            self.cart.pop(idx)
            self._refresh_cart_tree()
            self._update_totals()
            return
        if not self._line_qty_stock_ok(it["product_id"], float(it["quantity"]), float(v)):
            return
        it["quantity"] = float(v)
        it["total"] = self._line_total(it)
        self._refresh_cart_tree()
        self._update_totals()

    def _line_discount(self) -> None:
        idx = self._selected_index()
        if idx is None:
            warning_message(self.window(), "POS", "Select a cart line.")
            return
        it = self.cart[idx]
        gross = float(it["quantity"]) * float(it["unit_price"])
        v, ok = QInputDialog.getDouble(
            self.window(),
            "Line discount",
            f"Discount (GMD) for line (max {format_money(gross)}):",
            float(it.get("discount_amount") or 0),
            0.0,
            gross,
            2,
        )
        if not ok:
            return
        v = max(0.0, min(float(v), gross))
        it["discount_amount"] = round(v, 2)
        it["total"] = self._line_total(it)
        self._refresh_cart_tree()
        self._update_totals()

    def _remove_selected_line(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        self.cart.pop(idx)
        self._refresh_cart_tree()
        self._update_totals()

    def _confirm_clear_cart(self) -> None:
        if not self.cart:
            return
        if ask_yes_no(self.window(), "Clear cart", "Remove all lines?"):
            self.clear_cart()

    def _refresh_cart_tree(self) -> None:
        self._cart_table.setRowCount(0)
        for i, it in enumerate(self.cart):
            it["total"] = self._line_total(it)
            self._cart_table.insertRow(i)
            vals = (
                it.get("code", ""),
                it.get("name", ""),
                f"{it['quantity']:g}" if float(it["quantity"]) == int(float(it["quantity"])) else f"{it['quantity']:.2f}",
                format_money(float(it["unit_price"])),
                format_money(float(it.get("discount_amount") or 0)),
                format_money(float(it["total"])),
            )
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                self._cart_table.setItem(i, c, cell)
        self._sync_cart_table_height()
        self._update_kpis_cart_lines()
        self._update_totals()

    def _sync_cart_table_height(self) -> None:
        """Short when empty; grows with cart lines up to max visible rows, then scrolls."""
        n = len(self.cart)
        visible = min(max(n, _CART_TABLE_MIN_ROWS), _CART_TABLE_MAX_ROWS)
        hdr = self._cart_table.horizontalHeader().height()
        if hdr < 8:
            hdr = 28
        frame = self._cart_table.frameWidth() * 2
        h = hdr + visible * _CART_TABLE_ROW_PX + max(frame, 4)
        self._cart_table.setFixedHeight(int(h))

    def _update_totals(self) -> None:
        t = self._sales.calculate_cart_total(self.cart)
        self._subtotal_lbl.setText(f"Subtotal: {format_money(t['subtotal'])}")
        line_disc = sum(float(x.get("discount_amount") or 0) for x in self.cart)
        self._disc_lbl.setText(f"Line discounts: {format_money(line_disc)}")
        self._total_lbl.setText(format_money(t["total"]))
        self._update_tender_display()

    def _on_payment_change(self) -> None:
        is_cash = self._payment_var == "CASH"
        self._tender_frame.setVisible(is_cash)
        if not is_cash:
            self._tender.clear()
        self._update_tender_display()

    def _update_tender_display(self) -> None:
        t = self._sales.calculate_cart_total(self.cart)
        total = t["total"]
        if self._payment_var != "CASH":
            self._change_lbl.setText("—")
            return
        raw = self._tender.text().strip().replace(",", "")
        if not raw:
            self._change_lbl.setText(format_money(0))
            return
        try:
            paid = float(raw)
        except ValueError:
            self._change_lbl.setText("—")
            return
        self._change_lbl.setText(format_money(max(0.0, paid - total)))

    def _complete_sale(self) -> None:
        if not self.cart:
            warning_message(self.window(), "POS", "Cart is empty.")
            return
        self._refresh_cart_tree()
        totals = self._sales.calculate_cart_total(self.cart)
        total = totals["total"]
        method = self._payment_var

        if method == "CASH":
            raw = self._tender.text().strip().replace(",", "")
            if not raw:
                warning_message(self.window(), "POS", "Enter amount received for cash sales.")
                return
            try:
                paid = float(raw)
            except ValueError:
                warning_message(self.window(), "POS", "Invalid amount received.")
                return
            if paid + 1e-9 < total:
                warning_message(
                    self.window(),
                    "POS",
                    f"Insufficient tender. Need {format_money(total)}, got {format_money(paid)}.",
                )
                return

        try:
            sale = self._sales.record_sale(
                self.cart,
                {
                    "method": method,
                    "customer_name": self._customer.text().strip(),
                    "cashier_name": cashier_display_name(getattr(self._main, "current_user", None)),
                },
            )
        except Exception as e:
            warning_message(self.window(), "POS", f"Sale failed: {e}")
            return

        if sale:
            ReceiptPreviewDialogQt(self._main, sale).exec()
        self.clear_cart()
        self.refresh()

    def clear_cart(self) -> None:
        self.cart = []
        self._tender.clear()
        self._customer.clear()
        self._refresh_cart_tree()

    def _update_kpis_cart_lines(self) -> None:
        if "lines" in self._kpi_labels:
            self._kpi_labels["lines"].setText(str(len(self.cart)))

    def _update_parked_kpi(self) -> None:
        if "parked" in self._kpi_labels:
            self._kpi_labels["parked"].setText(str(len(self._parked)))

    def _refresh_parked_from_db(self) -> None:
        self._parked = self._parked_svc.list_tickets()
        self._update_parked_kpi()

    def _park_sale(self) -> None:
        if not self.cart:
            warning_message(self.window(), "POS", "Cart is empty — nothing to park.")
            return
        if self._parked_svc.count() >= MAX_PARKED_TICKETS:
            warning_message(
                self.window(),
                "POS",
                f"Maximum {MAX_PARKED_TICKETS} parked tickets. Recall or complete one first.",
            )
            return
        tid = uuid.uuid4().hex[:10]
        cart_snapshot = copy.deepcopy(self.cart)
        try:
            self._parked_svc.insert(
                tid,
                cart_snapshot,
                self._customer.text(),
                self._payment_var,
                self._tender.text(),
            )
        except ValueError as e:
            warning_message(self.window(), "POS", str(e))
            return
        except Exception as e:
            warning_message(self.window(), "POS", f"Could not park sale: {e}")
            return
        self.clear_cart()
        self._refresh_parked_from_db()
        info_message(self.window(), "POS", f"Parked ticket {tid} (saved).")
        self._search.setFocus()

    def _restore_ticket(self, ticket: dict) -> None:
        self.cart = copy.deepcopy(ticket.get("cart") or [])
        self._customer.setText(ticket.get("customer") or "")
        raw = str(ticket.get("payment") or "CASH").upper()
        # UI only offers Cash + mobile; map legacy parked methods to the closest option.
        if raw in ("CARD", "CHECK"):
            raw = "MOBILE"
        self._payment_var = raw if raw in ("CASH", "MOBILE") else "CASH"
        want = "Cash" if self._payment_var == "CASH" else "Mobile money"
        for b in self._pay_group.buttons():
            if b.text() == want:
                b.setChecked(True)
                break
        self._on_payment_change()
        self._tender.setText(ticket.get("tender") or "")
        self._refresh_cart_tree()

    def _merge_ticket_lines(self, ticket: dict) -> bool:
        for src in ticket.get("cart") or []:
            p = self._products.get_product(int(src["product_id"]))
            if not p:
                warning_message(
                    self.window(),
                    "POS",
                    f"Product #{src['product_id']} missing — merge aborted.",
                )
                return False
            if not self._ensure_sellable(p):
                return False
            q = float(src["quantity"])
            if not self._stock_available(p, q):
                return False
        for src in ticket.get("cart") or []:
            pid = int(src["product_id"])
            up = float(src["unit_price"])
            disc = float(src.get("discount_amount") or 0)
            q = float(src["quantity"])
            merged = False
            for it in self.cart:
                if (
                    it["product_id"] == pid
                    and abs(float(it["unit_price"]) - up) < 1e-9
                    and abs(float(it.get("discount_amount") or 0) - disc) < 1e-9
                ):
                    it["quantity"] = float(it["quantity"]) + q
                    it["total"] = self._line_total(it)
                    merged = True
                    break
            if not merged:
                nl = copy.deepcopy(src)
                nl["total"] = self._line_total(nl)
                self.cart.append(nl)
        self._refresh_cart_tree()
        return True

    def _recall_parked(self) -> None:
        if not self._parked:
            warning_message(self.window(), "POS", "No parked sales.")
            return
        d = RecallParkedDialogQt(self.window(), self._parked)
        if d.exec() != QDialog.DialogCode.Accepted or d.result is None:
            return
        idx = d.result
        ticket = self._parked.pop(idx)
        if self.cart:
            r = ask_yes_no_cancel(
                self.window(),
                "Current cart",
                "Replace current cart with the parked sale?\n\n"
                "Yes = replace\n"
                "No = merge parked lines into this cart\n"
                "Cancel = put ticket back",
            )
            if r == QMessageBox.Cancel:
                self._parked.insert(idx, ticket)
                return
            if r == QMessageBox.Yes:
                self._restore_ticket(ticket)
            elif not self._merge_ticket_lines(ticket):
                self._parked.insert(idx, ticket)
                return
        else:
            self._restore_ticket(ticket)
        try:
            self._parked_svc.delete(int(ticket["db_id"]))
        except (KeyError, TypeError, ValueError):
            pass
        self._refresh_parked_from_db()
        self._search.setFocus()

    def apply_global_lookup(self, text: str) -> None:
        """Top-bar search: focus POS lookup with text (user presses Enter to add)."""
        self._search.setText(text)
        self._search.setFocus()

    def refresh(self) -> None:
        t = self._sales.get_todays_totals()
        cash = self._sales.get_todays_cash_total()
        if "invoices" in self._kpi_labels:
            self._kpi_labels["invoices"].setText(str(t.get("invoice_count", 0)))
        if "gross" in self._kpi_labels:
            self._kpi_labels["gross"].setText(format_money(float(t.get("gross_total", 0))))
        if "cash" in self._kpi_labels:
            self._kpi_labels["cash"].setText(format_money(cash))
        self._update_kpis_cart_lines()
        self._refresh_parked_from_db()
        self._sync_cart_table_height()
        self._search.setFocus()
