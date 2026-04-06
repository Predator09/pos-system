"""Purchases screen — PySide6; uses PurchaseService + ProductService."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import PAD_MD
from app.services.product_service import ProductService
from app.services.purchase_service import PurchaseService
from app.services.supplier_service import SupplierService

from app.ui.helpers import format_purchase_timestamp
from app.ui_qt.dialogs_qt import PickProductDialogQt
from app.ui_qt.helpers_qt import format_money, info_message, warning_message
from app.ui_qt.supplier_editor_qt import SupplierEditorDialogQt

_LINE_COLS = ("code", "name", "qty", "ucost", "total")
_HIST_COLS = ("ref", "at", "supplier", "phone", "email", "lines", "value")
_SUP_DIR_COLS = ("name", "phone", "email")


class PurchasesView(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._products = ProductService()
        self._purchases = PurchaseService()
        self._suppliers = SupplierService()
        self._lines: list[dict] = []
        self._pending_product: dict | None = None
        self._linked_supplier_id: int | None = None
        self._supplier_combo_ids: list[int | None] = []
        self._filling_supplier_fields = False
        self._suppress_supplier_combo = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(PAD_MD)

        title = QLabel("Purchases")
        title.setObjectName("title")
        root.addWidget(title)
        sub = QLabel(
            "Add supplier lines, then click Purchase. On-hand quantity increases; optional weighted-average cost update.",
        )
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        root.addWidget(sub)

        dir_card = QFrame()
        dir_card.setObjectName("card")
        dv = QVBoxLayout(dir_card)
        dv.setContentsMargins(16, 14, 16, 14)
        dv.addWidget(QLabel("Registered suppliers (for future reference & quick fill)"))
        self._supplier_dir = QTableWidget(0, len(_SUP_DIR_COLS))
        self._supplier_dir.setHorizontalHeaderLabels(["Name", "Phone", "Email"])
        self._supplier_dir.setSelectionBehavior(QTableWidget.SelectRows)
        self._supplier_dir.setSelectionMode(QTableWidget.SingleSelection)
        self._supplier_dir.verticalHeader().setVisible(False)
        self._supplier_dir.setMaximumHeight(180)
        self._supplier_dir.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._supplier_dir.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._supplier_dir.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._supplier_dir.doubleClicked.connect(lambda *_: self._apply_selected_supplier_to_form())
        dv.addWidget(self._supplier_dir)

        dbtn = QHBoxLayout()
        nb = QPushButton("New supplier")
        nb.setCursor(Qt.PointingHandCursor)
        nb.clicked.connect(self._new_supplier)
        dbtn.addWidget(nb)
        eb = QPushButton("Edit selected")
        eb.setObjectName("ghost")
        eb.setCursor(Qt.PointingHandCursor)
        eb.clicked.connect(self._edit_supplier)
        dbtn.addWidget(eb)
        ub = QPushButton("Use for this receipt")
        ub.setCursor(Qt.PointingHandCursor)
        ub.clicked.connect(self._apply_selected_supplier_to_form)
        dbtn.addWidget(ub)
        rb = QPushButton("Refresh list")
        rb.setObjectName("ghost")
        rb.setCursor(Qt.PointingHandCursor)
        rb.clicked.connect(lambda: self._reload_suppliers(preserve_pick=False))
        dbtn.addWidget(rb)
        dbtn.addStretch(1)
        dv.addLayout(dbtn)
        root.addWidget(dir_card)

        hdr = QFrame()
        hdr.setObjectName("card")
        hl = QGridLayout(hdr)
        hl.setContentsMargins(16, 14, 16, 14)
        hl.addWidget(QLabel("Quick pick"), 0, 0)
        self._supplier_combo = QComboBox()
        self._supplier_combo.setMinimumWidth(320)
        self._supplier_combo.currentIndexChanged.connect(self._on_supplier_combo_changed)
        hl.addWidget(self._supplier_combo, 0, 1)
        hl.addWidget(QLabel("Supplier (this receipt)"), 1, 0)
        self._supplier = QLineEdit()
        self._supplier.textChanged.connect(self._on_supplier_field_edited)
        hl.addWidget(self._supplier, 1, 1)
        hl.addWidget(QLabel("Phone"), 2, 0)
        self._supplier_phone = QLineEdit()
        self._supplier_phone.setMinimumWidth(200)
        self._supplier_phone.textChanged.connect(self._on_supplier_field_edited)
        hl.addWidget(self._supplier_phone, 2, 1)
        hl.addWidget(QLabel("Email"), 3, 0)
        self._supplier_email = QLineEdit()
        self._supplier_email.setMinimumWidth(200)
        self._supplier_email.textChanged.connect(self._on_supplier_field_edited)
        hl.addWidget(self._supplier_email, 3, 1)
        self._wac = QCheckBox("Update product cost (weighted average with existing stock)")
        self._wac.setChecked(True)
        hl.addWidget(self._wac, 4, 1)
        root.addWidget(hdr)

        self._reload_suppliers(preserve_pick=False)

        add_card = QFrame()
        add_card.setObjectName("card")
        al = QHBoxLayout(add_card)
        al.setContentsMargins(16, 14, 16, 14)
        al.addWidget(QLabel("Qty"))
        self._qty = QLineEdit("1")
        self._qty.setFixedWidth(72)
        al.addWidget(self._qty)
        al.addWidget(QLabel("Unit cost (GMD)"))
        self._ucost = QLineEdit()
        self._ucost.setFixedWidth(100)
        al.addWidget(self._ucost)
        pp = QPushButton("Pick product…")
        pp.setCursor(Qt.PointingHandCursor)
        pp.clicked.connect(self._pick_product)
        al.addWidget(pp)
        ad = QPushButton("Add line")
        ad.setObjectName("primary")
        ad.setCursor(Qt.PointingHandCursor)
        ad.clicked.connect(self._add_line)
        al.addWidget(ad)
        rm = QPushButton("Remove selected")
        rm.setObjectName("ghost")
        rm.setCursor(Qt.PointingHandCursor)
        rm.clicked.connect(self._remove_line)
        al.addWidget(rm)
        al.addStretch(1)
        self._draft_lbl = QLabel("Draft total: " + format_money(0))
        self._draft_lbl.setObjectName("muted")
        al.addWidget(self._draft_lbl)
        root.addWidget(add_card)

        self._line_table = QTableWidget(0, len(_LINE_COLS))
        self._line_table.setHorizontalHeaderLabels(["Product code", "Product", "Qty", "Unit cost", "Line total"])
        self._line_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._line_table.setSelectionMode(QTableWidget.SingleSelection)
        root.addWidget(self._line_table, 1)

        act = QHBoxLayout()
        post = QPushButton("Purchase")
        post.setObjectName("primary")
        post.setCursor(Qt.PointingHandCursor)
        post.clicked.connect(self._post_receipt)
        act.addWidget(post)
        clr = QPushButton("Clear draft")
        clr.setObjectName("ghost")
        clr.setCursor(Qt.PointingHandCursor)
        clr.clicked.connect(self._clear_draft)
        act.addWidget(clr)
        act.addStretch(1)
        root.addLayout(act)

        root.addWidget(QLabel("Recent purchases"))
        self._hist_table = QTableWidget(0, len(_HIST_COLS))
        self._hist_table.setHorizontalHeaderLabels(
            ["Reference", "Date & time", "Supplier", "Phone", "Email", "Lines", "Value"]
        )
        self._hist_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._hist_table.setColumnWidth(1, 168)
        root.addWidget(self._hist_table, 1)

    def _on_supplier_field_edited(self, *_args) -> None:
        if self._filling_supplier_fields:
            return
        self._linked_supplier_id = None
        self._set_supplier_combo_manual()

    def _set_supplier_combo_manual(self) -> None:
        self._suppress_supplier_combo = True
        try:
            self._supplier_combo.blockSignals(True)
            self._supplier_combo.setCurrentIndex(0)
        finally:
            self._supplier_combo.blockSignals(False)
            self._suppress_supplier_combo = False

    def _on_supplier_combo_changed(self, idx: int) -> None:
        if self._suppress_supplier_combo or idx < 0:
            return
        if idx == 0 or idx >= len(self._supplier_combo_ids):
            self._linked_supplier_id = None
            return
        sid = self._supplier_combo_ids[idx]
        if sid is None:
            self._linked_supplier_id = None
            return
        row = self._suppliers.get(int(sid))
        if not row:
            self._reload_suppliers(preserve_pick=False)
            return
        self._filling_supplier_fields = True
        try:
            self._supplier.blockSignals(True)
            self._supplier_phone.blockSignals(True)
            self._supplier_email.blockSignals(True)
            self._supplier.setText(row.get("name") or "")
            self._supplier_phone.setText(row.get("phone") or "")
            self._supplier_email.setText(row.get("email") or "")
        finally:
            self._supplier.blockSignals(False)
            self._supplier_phone.blockSignals(False)
            self._supplier_email.blockSignals(False)
            self._filling_supplier_fields = False
        self._linked_supplier_id = int(sid)

    def _reload_suppliers(self, *, preserve_pick: bool) -> None:
        saved_id = self._linked_supplier_id if preserve_pick else None
        rows = self._suppliers.list_active()
        self._supplier_dir.setRowCount(0)
        for r in rows:
            i = self._supplier_dir.rowCount()
            self._supplier_dir.insertRow(i)
            self._supplier_dir.setItem(i, 0, QTableWidgetItem((r.get("name") or "")[:48]))
            self._supplier_dir.setItem(i, 1, QTableWidgetItem((r.get("phone") or "")[:28]))
            self._supplier_dir.setItem(i, 2, QTableWidgetItem((r.get("email") or "")[:40]))
            for c in range(3):
                it = self._supplier_dir.item(i, c)
                if it is not None:
                    it.setData(Qt.ItemDataRole.UserRole, int(r["id"]))
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)

        self._supplier_combo_ids = [None]
        self._suppress_supplier_combo = True
        self._supplier_combo.blockSignals(True)
        self._supplier_combo.clear()
        self._supplier_combo.addItem("— Type below or pick from list —")
        for r in rows:
            nm = (r.get("name") or "").strip() or f"#{r['id']}"
            extra = []
            if r.get("phone"):
                extra.append(str(r["phone"])[:16])
            lab = f"{nm} ({', '.join(extra)})" if extra else nm
            self._supplier_combo.addItem(lab[:72])
            self._supplier_combo_ids.append(int(r["id"]))

        if saved_id is not None and saved_id in self._supplier_combo_ids:
            idx = self._supplier_combo_ids.index(saved_id)
            self._supplier_combo.setCurrentIndex(idx)
            self._linked_supplier_id = saved_id
        else:
            self._supplier_combo.setCurrentIndex(0)
            self._linked_supplier_id = None
        self._supplier_combo.blockSignals(False)
        self._suppress_supplier_combo = False

    def _selected_supplier_id_from_table(self) -> int | None:
        r = self._supplier_dir.currentRow()
        if r < 0:
            return None
        it = self._supplier_dir.item(r, 0)
        if it is None:
            return None
        v = it.data(Qt.ItemDataRole.UserRole)
        return int(v) if v is not None else None

    def _new_supplier(self) -> None:
        d = SupplierEditorDialogQt(self.window(), self._suppliers, None)
        if d.exec() == QDialog.DialogCode.Accepted and getattr(d, "saved", False):
            self._reload_suppliers(preserve_pick=True)

    def _edit_supplier(self) -> None:
        sid = self._selected_supplier_id_from_table()
        if sid is None:
            warning_message(self.window(), "Suppliers", "Select a supplier in the list first.")
            return
        d = SupplierEditorDialogQt(self.window(), self._suppliers, sid)
        if d.exec() == QDialog.DialogCode.Accepted and getattr(d, "saved", False):
            self._reload_suppliers(preserve_pick=True)

    def _apply_selected_supplier_to_form(self) -> None:
        sid = self._selected_supplier_id_from_table()
        if sid is None:
            warning_message(self.window(), "Suppliers", "Select a supplier in the list first.")
            return
        row = self._suppliers.get(sid)
        if not row:
            self._reload_suppliers(preserve_pick=False)
            return
        try:
            idx = self._supplier_combo_ids.index(sid)
        except ValueError:
            idx = -1
        self._suppress_supplier_combo = True
        self._supplier_combo.blockSignals(True)
        try:
            if idx > 0:
                self._supplier_combo.setCurrentIndex(idx)
        finally:
            self._supplier_combo.blockSignals(False)
            self._suppress_supplier_combo = False
        self._filling_supplier_fields = True
        try:
            self._supplier.blockSignals(True)
            self._supplier_phone.blockSignals(True)
            self._supplier_email.blockSignals(True)
            self._supplier.setText(row.get("name") or "")
            self._supplier_phone.setText(row.get("phone") or "")
            self._supplier_email.setText(row.get("email") or "")
        finally:
            self._supplier.blockSignals(False)
            self._supplier_phone.blockSignals(False)
            self._supplier_email.blockSignals(False)
            self._filling_supplier_fields = False
        self._linked_supplier_id = sid

    def _pick_product(self) -> None:
        d = PickProductDialogQt(self.window(), self._products)
        if d.exec() == QDialog.DialogCode.Accepted and d.result:
            self._pending_product = d.result
            c = float(d.result.get("cost_price") or 0)
            self._ucost.setText(str(c) if c else "")

    def _add_line(self) -> None:
        if self._pending_product:
            p = self._pending_product
            self._pending_product = None
        else:
            d = PickProductDialogQt(self.window(), self._products)
            if d.exec() != QDialog.DialogCode.Accepted or not d.result:
                return
            p = d.result
        pid = int(p["id"])
        try:
            qty = float(self._qty.text().strip().replace(",", "") or "0")
        except ValueError:
            warning_message(self.window(), "Receiving", "Enter a valid quantity.")
            return
        if qty <= 0:
            warning_message(self.window(), "Receiving", "Quantity must be greater than zero.")
            return
        raw = self._ucost.text().strip().replace(",", "")
        if not raw:
            uc = float(p.get("cost_price") or 0)
        else:
            try:
                uc = float(raw)
            except ValueError:
                warning_message(self.window(), "Receiving", "Enter a valid unit cost.")
                return
        if uc < 0:
            warning_message(self.window(), "Receiving", "Unit cost cannot be negative.")
            return
        lt = round(qty * uc, 2)
        self._lines.append(
            {
                "product_id": pid,
                "code": p.get("code") or "",
                "name": p.get("name") or "",
                "quantity": qty,
                "unit_cost": uc,
                "line_total": lt,
            }
        )
        self._refresh_line_table()
        self._qty.setText("1")

    def _remove_line(self) -> None:
        r = self._line_table.currentRow()
        if r < 0 or r >= len(self._lines):
            return
        del self._lines[r]
        self._refresh_line_table()

    def _refresh_line_table(self) -> None:
        self._line_table.setRowCount(0)
        total = 0.0
        for row in self._lines:
            total += float(row["line_total"])
            i = self._line_table.rowCount()
            self._line_table.insertRow(i)
            q = row["quantity"]
            qv = f"{q:g}" if float(q) == int(float(q)) else f"{q:.2f}"
            vals = (row["code"], row["name"], qv, format_money(row["unit_cost"]), format_money(row["line_total"]))
            for c, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self._line_table.setItem(i, c, it)
        self._draft_lbl.setText("Draft total: " + format_money(total))

    def _clear_draft(self) -> None:
        self._lines.clear()
        self._filling_supplier_fields = True
        try:
            self._supplier.blockSignals(True)
            self._supplier_phone.blockSignals(True)
            self._supplier_email.blockSignals(True)
            self._supplier.clear()
            self._supplier_phone.clear()
            self._supplier_email.clear()
        finally:
            self._supplier.blockSignals(False)
            self._supplier_phone.blockSignals(False)
            self._supplier_email.blockSignals(False)
            self._filling_supplier_fields = False
        self._linked_supplier_id = None
        self._set_supplier_combo_manual()
        self._pending_product = None
        self._refresh_line_table()

    def _post_receipt(self) -> None:
        if not self._lines:
            warning_message(self.window(), "Purchases", "Add at least one line before purchasing.")
            return
        try:
            result = self._purchases.receive_receipt(
                [
                    {"product_id": x["product_id"], "quantity": x["quantity"], "unit_cost": x["unit_cost"]}
                    for x in self._lines
                ],
                supplier_name=self._supplier.text().strip() or None,
                supplier_phone=self._supplier_phone.text().strip() or None,
                supplier_email=self._supplier_email.text().strip() or None,
                supplier_id=self._linked_supplier_id,
                update_average_cost=self._wac.isChecked(),
            )
        except ValueError as e:
            warning_message(self.window(), "Purchases", str(e))
            return
        except Exception as e:
            warning_message(self.window(), "Purchases", f"Could not complete purchase: {e}")
            return
        info_message(
            self.window(),
            "Purchase recorded",
            f"{result['reference']}\n{result['line_count']} line(s) · {format_money(result['total_value'])}",
        )
        self._clear_draft()
        self.refresh()

    def refresh(self) -> None:
        self._reload_suppliers(preserve_pick=True)
        self._hist_table.setRowCount(0)
        for r in self._purchases.list_recent_receipts(40):
            i = self._hist_table.rowCount()
            self._hist_table.insertRow(i)
            vals = (
                r.get("reference") or "",
                format_purchase_timestamp(r.get("received_at") or r.get("created_at")),
                (r.get("supplier_name") or "")[:40],
                (r.get("supplier_phone") or "")[:32],
                (r.get("supplier_email") or "")[:40],
                str(int(r.get("line_count") or 0)),
                format_money(float(r.get("total_value") or 0)),
            )
            for c, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self._hist_table.setItem(i, c, it)
