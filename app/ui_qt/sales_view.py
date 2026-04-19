"""Point of sale Qt view; same SalesService / ProductService / ParkedSalesService flows as Tk."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox,
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

from app.config import PAD_LG, PAD_MD, PAD_SM
from app.services.parked_sales_service import MAX_PARKED_TICKETS, ParkedSalesService
from app.services.product_service import ProductService
from app.services.sales_service import SalesService, cashier_display_name
from app.ui_qt.presenters.sales_presenter import SalesPresenter

from app.ui_qt.dialogs_qt import (
    CreditMemoPreviewDialogQt,
    PickProductDialogQt,
    ProcessReturnDialogQt,
    ReceiptPreviewDialogQt,
    RecallParkedDialogQt,
)
from app.ui_qt.helpers_qt import ask_yes_no, ask_yes_no_cancel, format_money, info_message, warning_message
from app.ui_qt.icon_utils import set_button_icon

# ===== CONSTANTS =====
_CART_COLS = ("code", "name", "qty", "price", "disc", "total")
_CART_TABLE_MIN_ROWS = 2
_CART_TABLE_MAX_ROWS = 18
_CART_TABLE_ROW_PX = 36
_QTY_STEP = 1.0
_QTY_BTN_SIZE = 24
_QTY_SPINBOX_WIDTH = 96
_QTY_SPIN_HEIGHT = 28
_QTY_COL_WIDTH = 168


# ===== QUANTITY ADJUSTMENT WIDGET =====
class QuantityAdjustWidget(QWidget):
    """Compact − / spin / + for cart table (avoids global spinbox padding clipping text)."""

    def __init__(self, product_id: int, qty: float, ceiling: float, parent=None):
        super().__init__(parent)
        self.setObjectName("cartQtyCell")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.product_id = product_id

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_m = QPushButton("−")
        self.btn_m.setObjectName("qtyAdjBtn")
        self.btn_m.setFixedSize(_QTY_BTN_SIZE, _QTY_BTN_SIZE)
        self.btn_m.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_m.setAutoRepeat(True)
        self.btn_m.setAutoRepeatDelay(300)
        self.btn_m.setAutoRepeatInterval(80)
        lay.addWidget(self.btn_m, 0, Qt.AlignmentFlag.AlignVCenter)

        mx = max(0.01, float(qty), ceiling)
        self.spin = QDoubleSpinBox()
        self.spin.setObjectName("cartQtySpin")
        self.spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin.setDecimals(2)
        self.spin.setRange(0.01, mx)
        self.spin.setSingleStep(_QTY_STEP)
        self.spin.setValue(float(qty))
        self.spin.setFixedSize(_QTY_SPINBOX_WIDTH, _QTY_SPIN_HEIGHT)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.spin, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_p = QPushButton("+")
        self.btn_p.setObjectName("qtyAdjBtn")
        self.btn_p.setFixedSize(_QTY_BTN_SIZE, _QTY_BTN_SIZE)
        self.btn_p.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_p.setAutoRepeat(True)
        self.btn_p.setAutoRepeatDelay(300)
        self.btn_p.setAutoRepeatInterval(80)
        lay.addWidget(self.btn_p, 0)


# ===== SCAN & ADD WIDGET =====
class ScanAddWidget(QWidget):
    """Left column widget: Product lookup and quantity input."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        title = QLabel("Scan & add")
        title.setObjectName("pageSubtitle")
        layout.addWidget(title)
        hint = QLabel("Search by product code, barcode, or name, then add to cart.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        
        # Grid: Qty + Lookup + Add/Browse buttons
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        
        l_qty = QLabel("Qty")
        l_qty.setObjectName("muted")
        l_lookup = QLabel("Lookup")
        l_lookup.setObjectName("muted")
        grid.addWidget(l_qty, 0, 0, alignment=Qt.AlignBottom | Qt.AlignLeft)
        grid.addWidget(l_lookup, 0, 1, alignment=Qt.AlignBottom | Qt.AlignLeft)
        
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setMinimum(0.01)
        self.qty_spin.setMaximum(9999.0)
        self.qty_spin.setValue(1.0)
        self.qty_spin.setDecimals(2)
        self.qty_spin.setFixedWidth(88)
        self.qty_spin.setFixedHeight(36)
        grid.addWidget(self.qty_spin, 1, 0, alignment=Qt.AlignTop)
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("PC, barcode scan, or name…")
        self.search.setFixedHeight(36)
        grid.addWidget(self.search, 1, 1, alignment=Qt.AlignTop)
        
        self.add_btn = QPushButton("Add")
        self.add_btn.setObjectName("primary")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setFixedHeight(36)
        self.add_btn.setMinimumWidth(76)
        grid.addWidget(self.add_btn, 1, 2, alignment=Qt.AlignTop)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("ghost")
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.setFixedHeight(36)
        self.browse_btn.setMinimumWidth(88)
        grid.addWidget(self.browse_btn, 1, 3, alignment=Qt.AlignTop)
        set_button_icon(self.add_btn, "fa5s.cart-plus")
        set_button_icon(self.browse_btn, "fa5s.search")
        
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        
        # Customer field
        cust_layout = QHBoxLayout()
        cust_layout.setSpacing(8)
        lc = QLabel("Customer (optional)")
        lc.setObjectName("muted")
        cust_layout.addWidget(lc)
        self.customer = QLineEdit()
        self.customer.setMinimumHeight(34)
        cust_layout.addWidget(self.customer, 1)
        layout.addLayout(cust_layout)
        
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.card)


# ===== CART TABLE WIDGET =====
class CartTableWidget(QWidget):
    """Cart line items table with line and ticket actions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        title = QLabel("Line items")
        title.setObjectName("pageSubtitle")
        layout.addWidget(title)
        
        # Table
        self.table = QTableWidget(0, len(_CART_COLS))
        self.table.setHorizontalHeaderLabels(["Code", "Product", "Qty", "Price", "Disc", "Line"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(_CART_TABLE_ROW_PX)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, _QTY_COL_WIDTH)
        for c in (0, 3, 4, 5):
            self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.table, 0)
        
        # Line actions
        act_row0 = QHBoxLayout()
        act_row0.setSpacing(8)
        line_tag = QLabel("Line")
        line_tag.setObjectName("muted")
        act_row0.addWidget(line_tag)
        
        self.discount_btn = self._make_action_btn("Discount")
        self.remove_btn = self._make_action_btn("Remove")
        self.remove_btn.setObjectName("danger")
        set_button_icon(self.discount_btn, "fa5s.percent")
        set_button_icon(self.remove_btn, "fa5s.trash-alt")

        act_row0.addWidget(self.discount_btn)
        act_row0.addWidget(self.remove_btn)
        act_row0.addStretch(1)
        layout.addLayout(act_row0)
        
        # Ticket actions
        act_row1 = QHBoxLayout()
        act_row1.setSpacing(8)
        tk_tag = QLabel("Ticket")
        tk_tag.setObjectName("muted")
        act_row1.addWidget(tk_tag)
        
        self.park_btn = self._make_action_btn("Park")
        self.recall_btn = self._make_action_btn("Recall")
        self.return_btn = self._make_action_btn("Return")
        self.clear_btn = self._make_action_btn("Clear cart", min_w=100)
        self.clear_btn.setObjectName("danger")
        set_button_icon(self.park_btn, "fa5s.pause-circle")
        set_button_icon(self.recall_btn, "fa5s.undo")
        set_button_icon(self.return_btn, "fa5s.reply")
        set_button_icon(self.clear_btn, "fa5s.times-circle")
        
        act_row1.addWidget(self.park_btn)
        act_row1.addWidget(self.recall_btn)
        act_row1.addWidget(self.return_btn)
        act_row1.addStretch(1)
        act_row1.addWidget(self.clear_btn)
        layout.addLayout(act_row1)
        
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.card)
    
    @staticmethod
    def _make_action_btn(text: str, min_w: int = 88) -> QPushButton:
        b = QPushButton(text)
        b.setCursor(Qt.PointingHandCursor)
        b.setMinimumHeight(32)
        b.setMinimumWidth(min_w)
        return b


# ===== CHECKOUT WIDGET =====
class CheckoutWidget(QWidget):
    """Right column widget: Totals, payment method, and checkout."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setMinimumWidth(288)
        self.card.setMaximumWidth(400)
        self.card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Totals
        self.subtotal_lbl = QLabel()
        self.disc_lbl = QLabel()
        layout.addWidget(self.subtotal_lbl)
        layout.addWidget(self.disc_lbl)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)
        
        # Total row
        tot_card = QFrame()
        tot_card.setObjectName("posTotalCard")
        tot_row = QHBoxLayout(tot_card)
        tot_row.setContentsMargins(12, 10, 12, 10)
        tot_row.setSpacing(10)
        total_caption = QLabel("Total")
        total_caption.setObjectName("section")
        tot_row.addWidget(total_caption)
        self.total_lbl = QLabel()
        self.total_lbl.setObjectName("posTotalValue")
        tot_row.addStretch(1)
        tot_row.addWidget(self.total_lbl)
        layout.addWidget(tot_card)
        
        # Payment method
        pay_grid = QGridLayout()
        pay_grid.setHorizontalSpacing(8)
        pay_grid.setVerticalSpacing(4)
        self.pay_group = QButtonGroup()
        pay_opts = (("Cash", "CASH"), ("Card", "CARD"), ("Mobile", "MOBILE"), ("Check", "CHECK"))
        self.payment_buttons = {}
        for i, (text, val) in enumerate(pay_opts):
            rb = QRadioButton(text)
            self.pay_group.addButton(rb)
            self.payment_buttons[val] = rb
            pay_grid.addWidget(rb, i // 2, i % 2)
            if val == "CASH":
                rb.setChecked(True)
        layout.addLayout(pay_grid)
        
        # Tender frame
        self.tender_frame = QWidget()
        tlay = QVBoxLayout(self.tender_frame)
        tlay.setContentsMargins(0, 0, 0, 0)
        tlay.setSpacing(6)
        tlay.addWidget(QLabel("Amount received"))
        self.tender = QLineEdit()
        self.tender.setMinimumHeight(34)
        tlay.addWidget(self.tender)
        ch_row = QHBoxLayout()
        ch_row.addWidget(QLabel("Change"))
        ch_row.addStretch(1)
        self.change_lbl = QLabel()
        self.change_lbl.setObjectName("kpiValueSm")
        ch_row.addWidget(self.change_lbl)
        tlay.addLayout(ch_row)
        layout.addWidget(self.tender_frame)
        
        # Action buttons
        self.complete_btn = QPushButton("Complete sale")
        self.complete_btn.setObjectName("success")
        self.complete_btn.setCursor(Qt.PointingHandCursor)
        self.complete_btn.setMinimumHeight(44)
        layout.addWidget(self.complete_btn)
        set_button_icon(self.complete_btn, "fa5s.check-circle")
        
        self.new_cart_btn = QPushButton("New cart")
        self.new_cart_btn.setObjectName("danger")
        self.new_cart_btn.setCursor(Qt.PointingHandCursor)
        self.new_cart_btn.setMinimumHeight(36)
        layout.addWidget(self.new_cart_btn)
        set_button_icon(self.new_cart_btn, "fa5s.ban")
        
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.card, 0, Qt.AlignmentFlag.AlignTop)
        outer.addStretch(1)


# ===== MAIN SALES VIEW =====
class SalesView(QWidget):
    """Point of sale register: manages cart, checkout, and parked sales."""
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._presenter = SalesPresenter(SalesService(), ProductService(), ParkedSalesService())
        self._sales = self._presenter.sales_service
        self._products = self._presenter.product_service
        self._parked_svc = self._presenter.parked_service
        
        # State
        self.cart: list[dict] = []
        self._parked: list[dict] = []
        self._kpi_labels: dict[str, QLabel] = {}
        self._payment_var = "CASH"
        self._cart_row_signatures: list[tuple] = []
        
        # Clock
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        
        # Build UI
        self._build_ui()
        self._connect_signals()
        
        # Init
        self._on_payment_change()
        QTimer.singleShot(0, self._sync_cart_table_height)
    
    def _build_ui(self):
        """Construct the complete sales view layout."""
        root = QVBoxLayout(self)
        root.setContentsMargins(PAD_SM, PAD_SM, PAD_SM, PAD_SM)
        root.setSpacing(PAD_MD)
        
        # Top KPI bar + clock
        self._build_top_bar()
        root.addWidget(self._top_bar)
        
        # Main: left (scan + cart) + right (checkout)
        body = QHBoxLayout()
        body.setSpacing(PAD_LG)
        
        # Left column
        left_col = QVBoxLayout()
        left_col.setSpacing(PAD_MD)
        left_col.setContentsMargins(0, 0, 0, 0)
        
        self._scan_widget = ScanAddWidget()
        left_col.addWidget(self._scan_widget.card)
        
        self._cart_widget = CartTableWidget()
        left_col.addWidget(self._cart_widget.card)
        left_col.addStretch(1)
        
        body.addLayout(left_col, stretch=3)
        
        # Right column (checkout)
        self._checkout_widget = CheckoutWidget()
        body.addWidget(self._checkout_widget.card, stretch=1, alignment=Qt.AlignmentFlag.AlignTop)
        
        root.addLayout(body, stretch=1)
    
    def _build_top_bar(self):
        """Build KPI metrics bar with live clock."""
        self._top_bar = QFrame()
        self._top_bar.setObjectName("card")
        top_row = QHBoxLayout(self._top_bar)
        top_row.setContentsMargins(PAD_MD, PAD_SM, PAD_MD, PAD_SM)
        top_row.setSpacing(PAD_MD)
        
        for key, title in (
            ("invoices", "Invoices"),
            ("net", "Net sales"),
            ("refunds", "Refunds"),
            ("cash", "Cash"),
            ("lines", "Cart lines"),
            ("parked", "Parked"),
        ):
            cell = QVBoxLayout()
            cell.setSpacing(PAD_SM // 2)
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
    
    def _connect_signals(self):
        """Wire up all signal/slot connections."""
        # Scan & add
        self._scan_widget.search.returnPressed.connect(self._on_add_product)
        self._scan_widget.add_btn.clicked.connect(self._on_add_product)
        self._scan_widget.browse_btn.clicked.connect(self._pick_product)
        
        # Cart actions
        self._cart_widget.discount_btn.clicked.connect(self._line_discount)
        self._cart_widget.remove_btn.clicked.connect(self._remove_selected_line)
        self._cart_widget.park_btn.clicked.connect(self._park_sale)
        self._cart_widget.recall_btn.clicked.connect(self._recall_parked)
        self._cart_widget.return_btn.clicked.connect(self._process_return)
        self._cart_widget.clear_btn.clicked.connect(self._confirm_clear_cart)
        
        # Payment
        for val, btn in self._checkout_widget.payment_buttons.items():
            btn.toggled.connect(lambda c, v=val: self._on_payment_toggled(c, v))
        self._checkout_widget.tender.textChanged.connect(self._update_tender_display)
        
        # Checkout
        self._checkout_widget.complete_btn.clicked.connect(self._complete_sale)
        self._checkout_widget.new_cart_btn.clicked.connect(self._confirm_clear_cart)
    
    # ===== UTILITY METHODS =====
    
    def _tick_clock(self) -> None:
        self._clock_lbl.setText(datetime.now().strftime("%H:%M:%S"))
    
    def _parse_qty(self) -> float:
        try:
            q = float(self._scan_widget.qty_spin.value())
            if q <= 0:
                raise ValueError
            return q
        except (TypeError, ValueError):
            return 0.0
    
    def _qty_in_cart_for(self, product_id: int) -> float:
        return self._presenter.qty_in_cart_for(self.cart, product_id)
    
    def _resolve_product(self, query: str):
        return self._presenter.resolve_product(query)
    
    def _ensure_sellable(self, p: dict) -> bool:
        if not self._presenter.is_sellable(p):
            warning_message(self.window(), "SmartStock", "This product is inactive.")
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
        ok, detail = self._presenter.stock_available(self.cart, p, add_qty)
        if ok:
            return True
        if self._offer_stock_override("Stock", detail):
            return True
        warning_message(self.window(), "Stock", detail)
        return False
    
    def _line_qty_stock_ok(self, product_id: int, current_line_qty: float, new_line_qty: float) -> bool:
        ok, detail = self._presenter.line_qty_stock_ok(self.cart, product_id, current_line_qty, new_line_qty)
        if ok:
            return True
        if self._offer_stock_override("Stock", detail):
            return True
        warning_message(self.window(), "Stock", detail)
        return False
    
    @staticmethod
    def _line_total(item: dict) -> float:
        return SalesPresenter.line_total(item)
    
    # ===== PRODUCT MANAGEMENT =====
    
    def _on_add_product(self) -> None:
        query = self._scan_widget.search.text()
        qty = self._parse_qty()
        if qty <= 0:
            warning_message(self.window(), "SmartStock", "Enter a valid quantity (> 0).")
            return
        
        resolved = self._resolve_product(query)
        if resolved is None:
            return
        if isinstance(resolved, list):
            if not resolved:
                warning_message(self.window(), "SmartStock", "No matching active products.")
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
        self._scan_widget.search.clear()
        self._scan_widget.qty_spin.setValue(1.0)
        self._scan_widget.search.setFocus()
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
    
    def add_to_cart_by_product_id(self, product_id: int, quantity: float = 1.0) -> None:
        q = float(quantity)
        if q <= 0:
            warning_message(self.window(), "SmartStock", "Quantity must be greater than zero.")
            return
        p = self._products.get_product(int(product_id))
        if not p:
            warning_message(self.window(), "SmartStock", "Product not found.")
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
        self._scan_widget.search.setFocus()
    
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
    
    # ===== CART LINE MANAGEMENT =====
    
    def _selected_index(self) -> int | None:
        r = self._cart_widget.table.currentRow()
        if r < 0 or r >= len(self.cart):
            return None
        return r
    
    def _line_discount(self) -> None:
        idx = self._selected_index()
        if idx is None:
            warning_message(self.window(), "SmartStock", "Select a cart line.")
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
    
    def _cart_index_for_product(self, product_id: int) -> int | None:
        pid = int(product_id)
        for i, it in enumerate(self.cart):
            if int(it["product_id"]) == pid:
                return i
        return None
    
    def _qty_line_ceiling(self, product_id: int, line_qty: float) -> float:
        p = self._products.get_product(int(product_id))
        if not p:
            return 99999.0
        have = float(p.get("quantity_in_stock") or 0)
        in_other = self._qty_in_cart_for(int(product_id)) - float(line_qty)
        return max(0.01, round(have - in_other + 1e-9, 4))
    
    def _cart_qty_delta(self, product_id: int, delta: float) -> None:
        idx = self._cart_index_for_product(product_id)
        if idx is None:
            return
        it = self.cart[idx]
        cur = float(it["quantity"])
        new_q = cur + float(delta)
        if new_q <= 0:
            self.cart.pop(idx)
            self._refresh_cart_tree()
            self._update_totals()
            return
        if new_q < 0.01:
            new_q = 0.01
        if not self._line_qty_stock_ok(int(product_id), cur, new_q):
            return
        it["quantity"] = new_q
        it["total"] = self._line_total(it)
        self._refresh_cart_tree()
        self._update_totals()
    
    def _cart_qty_commit(self, product_id: int, value: float) -> None:
        idx = self._cart_index_for_product(product_id)
        if idx is None:
            return
        it = self.cart[idx]
        cur = float(it["quantity"])
        v = float(value)
        if v <= 0:
            self.cart.pop(idx)
            self._refresh_cart_tree()
            self._update_totals()
            return
        if v < 0.01:
            v = 0.01
        if not self._line_qty_stock_ok(int(product_id), cur, v):
            self._refresh_cart_tree()
            self._update_totals()
            return
        it["quantity"] = v
        it["total"] = self._line_total(it)
        self._refresh_cart_tree()
        self._update_totals()
    
    def _make_qty_cell_widget(self, product_id: int, qty: float) -> QuantityAdjustWidget:
        """Create quantity widget for cart table cell."""
        ceiling = self._qty_line_ceiling(product_id, qty)
        widget = QuantityAdjustWidget(product_id, qty, ceiling, self)
        
        pid = int(product_id)
        widget.btn_m.clicked.connect(lambda: self._cart_qty_delta(pid, -_QTY_STEP))
        widget.btn_p.clicked.connect(lambda: self._cart_qty_delta(pid, _QTY_STEP))
        widget.spin.editingFinished.connect(lambda: self._cart_qty_commit(pid, widget.spin.value()))
        
        return widget

    @staticmethod
    def _set_readonly_text_cell(table: QTableWidget, row: int, col: int, value: str) -> None:
        cell = table.item(row, col)
        if cell is None:
            cell = QTableWidgetItem(value)
            cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, col, cell)
            return
        if cell.text() != value:
            cell.setText(value)

    def _cart_row_signature(self, it: dict) -> tuple:
        """Stable snapshot used to update only changed cart rows."""
        return (
            int(it["product_id"]),
            str(it.get("code") or ""),
            str(it.get("name") or ""),
            round(float(it["quantity"]), 4),
            round(float(it["unit_price"]), 4),
            round(float(it.get("discount_amount") or 0), 4),
            round(float(it["total"]), 4),
            round(self._qty_line_ceiling(int(it["product_id"]), float(it["quantity"])), 4),
        )

    def _render_cart_row(self, row: int, it: dict) -> tuple:
        qty_col = _CART_COLS.index("qty")
        self._set_readonly_text_cell(self._cart_widget.table, row, 0, str(it.get("code", "")))
        self._set_readonly_text_cell(self._cart_widget.table, row, 1, str(it.get("name", "")))
        self._set_readonly_text_cell(
            self._cart_widget.table, row, 3, format_money(float(it["unit_price"]))
        )
        self._set_readonly_text_cell(
            self._cart_widget.table, row, 4, format_money(float(it.get("discount_amount") or 0))
        )
        self._set_readonly_text_cell(self._cart_widget.table, row, 5, format_money(float(it["total"])))
        self._cart_widget.table.setCellWidget(
            row, qty_col, self._make_qty_cell_widget(int(it["product_id"]), float(it["quantity"]))
        )
        return self._cart_row_signature(it)
    
    def _refresh_cart_tree(self) -> None:
        """Update cart table using row diffs; avoid full rebuild when possible."""
        table = self._cart_widget.table
        selected = table.currentRow()
        prev_count = table.rowCount()
        new_count = len(self.cart)

        for it in self.cart:
            it["total"] = self._line_total(it)

        if prev_count < new_count:
            for _ in range(new_count - prev_count):
                table.insertRow(table.rowCount())
        elif prev_count > new_count:
            for _ in range(prev_count - new_count):
                table.removeRow(table.rowCount() - 1)

        next_signatures: list[tuple] = []
        for i, it in enumerate(self.cart):
            sig = self._cart_row_signature(it)
            old_sig = self._cart_row_signatures[i] if i < len(self._cart_row_signatures) else None
            if sig != old_sig:
                sig = self._render_cart_row(i, it)
            next_signatures.append(sig)

        self._cart_row_signatures = next_signatures

        if selected >= 0 and new_count:
            table.setCurrentCell(min(selected, new_count - 1), 0)

        self._sync_cart_table_height()
        self._update_kpis_cart_lines()
        self._update_totals()
    
    def _sync_cart_table_height(self) -> None:
        """Adjust table height based on row count."""
        n = len(self.cart)
        visible = min(max(n, _CART_TABLE_MIN_ROWS), _CART_TABLE_MAX_ROWS)
        hdr = self._cart_widget.table.horizontalHeader().height()
        if hdr < 8:
            hdr = 28
        frame = self._cart_widget.table.frameWidth() * 2
        h = hdr + visible * _CART_TABLE_ROW_PX + max(frame, 4)
        self._cart_widget.table.setFixedHeight(int(h))
    
    def clear_cart(self) -> None:
        self.cart = []
        self._cart_row_signatures = []
        self._checkout_widget.tender.clear()
        self._scan_widget.customer.clear()
        self._refresh_cart_tree()
    
    # ===== TOTALS & PAYMENT =====
    
    def _update_totals(self) -> None:
        t = self._presenter.calculate_cart_total(self.cart)
        self._checkout_widget.subtotal_lbl.setText(f"Subtotal: {format_money(t['subtotal'])}")
        line_disc = sum(float(x.get("discount_amount") or 0) for x in self.cart)
        self._checkout_widget.disc_lbl.setText(f"Line discounts: {format_money(line_disc)}")
        self._checkout_widget.total_lbl.setText(format_money(t["total"]))
        self._update_tender_display()
    
    def _on_payment_toggled(self, checked: bool, val: str) -> None:
        if checked:
            self._payment_var = val
            self._on_payment_change()
    
    def _on_payment_change(self) -> None:
        is_cash = self._payment_var == "CASH"
        self._checkout_widget.tender_frame.setVisible(is_cash)
        if not is_cash:
            self._checkout_widget.tender.clear()
        self._update_tender_display()
    
    def _update_tender_display(self) -> None:
        t = self._presenter.calculate_cart_total(self.cart)
        total = t["total"]
        if self._payment_var != "CASH":
            self._checkout_widget.change_lbl.setText("—")
            return
        raw = self._checkout_widget.tender.text().strip().replace(",", "")
        if not raw:
            self._checkout_widget.change_lbl.setText(format_money(0))
            return
        try:
            paid = float(raw)
        except ValueError:
            self._checkout_widget.change_lbl.setText("—")
            return
        self._checkout_widget.change_lbl.setText(format_money(max(0.0, paid - total)))
    
    def _complete_sale(self) -> None:
        if not self.cart:
            warning_message(self.window(), "SmartStock", "Cart is empty.")
            return
        self._refresh_cart_tree()
        totals = self._presenter.calculate_cart_total(self.cart)
        total = totals["total"]
        method = self._payment_var
        
        if method == "CASH":
            raw = self._checkout_widget.tender.text().strip().replace(",", "")
            if not raw:
                warning_message(self.window(), "SmartStock", "Enter amount received for cash sales.")
                return
            try:
                paid = float(raw)
            except ValueError:
                warning_message(self.window(), "SmartStock", "Invalid amount received.")
                return
            if paid + 1e-9 < total:
                warning_message(
                    self.window(),
                    "SmartStock",
                    f"Insufficient tender. Need {format_money(total)}, got {format_money(paid)}.",
                )
                return
        
        try:
            sale = self._sales.record_sale(
                self.cart,
                {
                    "method": method,
                    "customer_name": self._scan_widget.customer.text().strip(),
                    "cashier_name": cashier_display_name(getattr(self._main, "current_user", None)),
                },
            )
        except Exception as e:
            warning_message(self.window(), "SmartStock", f"Sale failed: {e}")
            return
        
        if sale:
            ReceiptPreviewDialogQt(self._main, sale).exec()
        self.clear_cart()
        self.refresh()
    
    # ===== KPI & UI UPDATES =====
    
    def _update_kpis_cart_lines(self) -> None:
        if "lines" in self._kpi_labels:
            self._kpi_labels["lines"].setText(str(len(self.cart)))
    
    def _update_parked_kpi(self) -> None:
        if "parked" in self._kpi_labels:
            self._kpi_labels["parked"].setText(str(len(self._parked)))
    
    def _refresh_parked_from_db(self) -> None:
        self._parked = self._parked_svc.list_tickets()
        self._update_parked_kpi()
    
    def refresh(self) -> None:
        t = self._sales.get_todays_totals()
        cash = self._sales.get_todays_cash_total()
        if "invoices" in self._kpi_labels:
            self._kpi_labels["invoices"].setText(str(t.get("invoice_count", 0)))
        if "net" in self._kpi_labels:
            self._kpi_labels["net"].setText(format_money(float(t.get("net_total", 0))))
        if "refunds" in self._kpi_labels:
            self._kpi_labels["refunds"].setText(format_money(float(t.get("refund_total", 0))))
        if "cash" in self._kpi_labels:
            self._kpi_labels["cash"].setText(format_money(cash))
        self._update_kpis_cart_lines()
        self._refresh_parked_from_db()
        self._sync_cart_table_height()
        self._scan_widget.search.setFocus()
    
    def _process_return(self) -> None:
        d = ProcessReturnDialogQt(self.window(), self._sales, self._main)
        if d.exec() != QDialog.DialogCode.Accepted or not d.memo:
            return
        CreditMemoPreviewDialogQt(self.window(), d.memo).exec()
        self.refresh()
    
    # ===== PARKED SALES =====
    
    def _park_sale(self) -> None:
        if not self.cart:
            warning_message(self.window(), "SmartStock", "Cart is empty — nothing to park.")
            return
        if self._parked_svc.count() >= MAX_PARKED_TICKETS:
            warning_message(
                self.window(),
                "SmartStock",
                f"Maximum {MAX_PARKED_TICKETS} parked tickets. Recall or complete one first.",
            )
            return
        tid = uuid.uuid4().hex[:10]
        cart_snapshot = copy.deepcopy(self.cart)
        try:
            self._parked_svc.insert(
                tid,
                cart_snapshot,
                self._scan_widget.customer.text(),
                self._payment_var,
                self._checkout_widget.tender.text(),
            )
        except ValueError as e:
            warning_message(self.window(), "SmartStock", str(e))
            return
        except Exception as e:
            warning_message(self.window(), "SmartStock", f"Could not park sale: {e}")
            return
        self.clear_cart()
        self._refresh_parked_from_db()
        info_message(self.window(), "SmartStock", f"Parked ticket {tid} (saved).")
        self._scan_widget.search.setFocus()
    
    def _restore_ticket(self, ticket: dict) -> None:
        self.cart = copy.deepcopy(ticket.get("cart") or [])
        self._scan_widget.customer.setText(ticket.get("customer") or "")
        raw = str(ticket.get("payment") or "CASH").upper()
        if raw in ("CARD", "CHECK"):
            raw = "MOBILE"
        self._payment_var = raw if raw in ("CASH", "MOBILE") else "CASH"
        want = "Cash" if self._payment_var == "CASH" else "Mobile"
        for b in self._checkout_widget.pay_group.buttons():
            if b.text() == want:
                b.setChecked(True)
                break
        self._on_payment_change()
        self._checkout_widget.tender.setText(ticket.get("tender") or "")
        self._refresh_cart_tree()
    
    def _merge_ticket_lines(self, ticket: dict) -> bool:
        for src in ticket.get("cart") or []:
            p = self._products.get_product(int(src["product_id"]))
            if not p:
                warning_message(
                    self.window(),
                    "SmartStock",
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
            warning_message(self.window(), "SmartStock", "No parked sales.")
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
        self._scan_widget.search.setFocus()
    
    def apply_global_lookup(self, text: str) -> None:
        """Top-bar search: focus sales screen lookup with text (user presses Enter to add)."""
        self._scan_widget.search.setText(text)
        self._scan_widget.search.setFocus()