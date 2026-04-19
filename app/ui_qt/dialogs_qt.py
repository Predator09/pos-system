"""Qt dialogs mirroring Tk PickProduct / Receipt / Recall flows."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QShowEvent
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.receipt_output import (
    archive_credit_memo_file,
    archive_receipt_file,
    format_credit_memo_plaintext,
    format_receipt_plaintext,
    print_credit_memo,
    print_receipt,
)
from app.services.sales_service import cashier_display_name
from app.config import PAD_LG, PAD_MD, PAD_SM
from app.ui.date_display import format_iso_date_as_display
from app.ui.helpers import format_purchase_timestamp
from app.services.shop_settings import ShopSettings
from app.ui_qt.icon_utils import set_button_icon, style_dialog_button_box
from app.ui_qt.helpers_qt import format_money, info_message, warning_message


class PickProductDialogQt(QDialog):
    def __init__(self, parent, product_service, products=None):
        super().__init__(parent)
        self.product_service = product_service
        self.result = None
        self._all_products = list(products) if products is not None else product_service.list_products()
        self._filtered = list(self._all_products)

        self.setWindowTitle("Pick Product")
        self.resize(520, 420)
        v = QVBoxLayout(self)
        v.setContentsMargins(PAD_MD, PAD_MD, PAD_MD, PAD_MD)
        v.setSpacing(PAD_MD)
        row = QHBoxLayout()
        row.setSpacing(PAD_SM)
        row.addWidget(QLabel("Filter:"))
        self._filter_edit = QLineEdit()
        self._filter_edit.textChanged.connect(self._apply_filter)
        row.addWidget(self._filter_edit, 1)
        v.addLayout(row)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._ok)
        v.addWidget(self._list, 1)
        self._populate_listbox()

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        style_dialog_button_box(bb, ok_icon="fa5s.check", cancel_icon="fa5s.times")
        v.addWidget(bb)

    def _apply_filter(self) -> None:
        q = self._filter_edit.text().strip().lower()
        if not q:
            self._filtered = list(self._all_products)
        else:
            self._filtered = [
                p
                for p in self._all_products
                if q in (p.get("name") or "").lower()
                or q in (p.get("code") or "").lower()
                or q in (p.get("barcode") or "").lower()
            ]
        self._populate_listbox()

    def _populate_listbox(self) -> None:
        self._list.clear()
        for p in self._filtered:
            sku = p.get("code", "") or ""
            bc = (p.get("barcode") or "").strip()
            extra = f" · {bc}" if bc else ""
            line = f"{p.get('name', '')} — PC {sku}{extra} — {format_money(float(p.get('selling_price', 0)))}"
            self._list.addItem(line)

    def _ok(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            info_message(self, "Pick Product", "Select a product.")
            return
        self.result = self._filtered[row]
        self.accept()


class PeriodSalesSummaryDialogQt(QDialog):
    """Read-only receipt-style summary for a date range (not a single invoice)."""

    def __init__(self, parent, start_date: str, end_date: str, body: str):
        super().__init__(parent)
        sd = format_iso_date_as_display(str(start_date or "")[:10])
        ed = format_iso_date_as_display(str(end_date or "")[:10])
        self.setWindowTitle(f"Period summary · {sd} — {ed}")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(420, 480)
        v = QVBoxLayout(self)
        v.setContentsMargins(PAD_MD, PAD_MD, PAD_MD, PAD_MD)
        v.setSpacing(PAD_MD)
        hint = QLabel(
            "Totals for the period you selected on the dashboard (all invoices in range). "
            "This is not a printable customer receipt."
        )
        hint.setWordWrap(True)
        v.addWidget(hint)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(body)
        v.addWidget(text, 1)
        done_btn = QPushButton("Done", clicked=self.accept)
        set_button_icon(done_btn, "fa5s.check-circle")
        v.addWidget(done_btn)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.raise_()
        self.activateWindow()


def _format_purchase_grn_plaintext(header: dict, lines: list[dict]) -> str:
    ref = header.get("reference") or "—"
    when = format_purchase_timestamp(header.get("received_at") or header.get("created_at"))
    sup = (header.get("supplier_name") or "").strip() or "—"
    phone = (header.get("supplier_phone") or "").strip() or "—"
    email = (header.get("supplier_email") or "").strip() or "—"
    notes = (header.get("notes") or "").strip()
    total = float(header.get("total_value") or 0)

    parts: list[str] = [
        "Goods receipt (GRN)",
        "",
        f"Reference:    {ref}",
        f"Date & time:  {when}",
        f"Supplier:     {sup}",
        f"Phone:        {phone}",
        f"Email:        {email}",
    ]
    if notes:
        parts.append(f"Notes:        {notes}")
    parts.extend(["", "Line items", ""])
    parts.append(f"{'PC':<12} {'Product':<34} {'Qty':>8} {'Unit':>12} {'Line total':>14}")
    parts.append("-" * 84)
    for ln in lines:
        code = str(ln.get("product_code") or "")[:12]
        name = str(ln.get("product_name") or "")[:34]
        q = float(ln.get("quantity") or 0)
        qstr = f"{q:g}" if q == int(q) else f"{q:.2f}"
        uc = float(ln.get("cost_price") or 0)
        lt = q * uc
        parts.append(f"{code:<12} {name:<34} {qstr:>8} {format_money(uc):>12} {format_money(lt):>14}")
    parts.append("-" * 84)
    parts.append(f"{'TOTAL':>70} {format_money(total):>14}")
    return "\n".join(parts)


class PurchaseReceiptDetailDialogQt(QDialog):
    """Read-only line-item detail for a posted goods receipt (GRN)."""

    def __init__(self, parent, purchase_service, receipt_id: int):
        super().__init__(parent)
        self.setWindowTitle("Purchase receipt — details")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(680, 520)
        v = QVBoxLayout(self)
        v.setContentsMargins(PAD_MD, PAD_MD, PAD_MD, PAD_MD)
        v.setSpacing(PAD_MD)
        header = purchase_service.get_receipt(receipt_id)
        if not header:
            v.addWidget(QLabel("This receipt could not be found — it may have been removed."))
            done_btn = QPushButton("Close", clicked=self.reject)
            set_button_icon(done_btn, "fa5s.times-circle")
            v.addWidget(done_btn)
            return
        lines = purchase_service.get_receipt_lines(receipt_id)
        hint = QLabel("Goods receipt lines (read-only).")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        v.addWidget(hint)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(_format_purchase_grn_plaintext(header, lines))
        v.addWidget(text, 1)
        done_btn = QPushButton("Done", clicked=self.accept)
        done_btn.setObjectName("primary")
        set_button_icon(done_btn, "fa5s.check-circle")
        v.addWidget(done_btn)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.raise_()
        self.activateWindow()


class ReceiptPreviewDialogQt(QDialog):
    def __init__(self, parent, sale: dict):
        super().__init__(parent)
        self._sale = sale
        self.setWindowTitle("Sale recorded — receipt")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(460, 560)
        v = QVBoxLayout(self)
        v.setContentsMargins(PAD_MD, PAD_MD, PAD_MD, PAD_MD)
        v.setSpacing(PAD_MD)
        hint = QLabel(
            "Print for the customer if needed. A copy is saved to this shop's receipts folder when you click Done "
            "(or use Save record anytime). "
        )
        hint.setWordWrap(True)
        v.addWidget(hint)
        lp = ShopSettings().get_logo_path()
        if lp and Path(lp).is_file():
            pix = QPixmap(lp)
            if not pix.isNull():
                logo_lab = QLabel()
                logo_lab.setPixmap(pix.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                logo_lab.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                v.addWidget(logo_lab)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(format_receipt_plaintext(sale))
        v.addWidget(text, 1)

        row = QHBoxLayout()
        row.setSpacing(PAD_SM)
        print_btn = QPushButton("Print receipt", clicked=self._do_print)
        save_btn = QPushButton("Save record", clicked=self._do_save)
        done_btn = QPushButton("Done", clicked=self._on_done)
        done_btn.setObjectName("primary")
        set_button_icon(print_btn, "fa5s.print")
        set_button_icon(save_btn, "fa5s.save")
        set_button_icon(done_btn, "fa5s.check-circle")
        row.addWidget(print_btn)
        row.addWidget(save_btn)
        row.addStretch(1)
        row.addWidget(done_btn)
        v.addLayout(row)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def _on_done(self) -> None:
        ok, msg = archive_receipt_file(self._sale)
        if not ok:
            warning_message(self, "Receipt not saved", msg)
        self.accept()

    def _do_print(self) -> None:
        ok, msg = print_receipt(self._sale)
        info_message(self, "Print" if ok else "Print failed", msg)

    def _do_save(self) -> None:
        ok, msg = archive_receipt_file(self._sale)
        info_message(self, "Record saved" if ok else "Save failed", msg)


class RecallParkedDialogQt(QDialog):
    def __init__(self, parent, tickets: list[dict]):
        super().__init__(parent)
        self.result: int | None = None
        self._tickets = list(tickets)
        self.setWindowTitle("Parked sales")
        self.resize(520, 360)
        v = QVBoxLayout(self)
        v.setContentsMargins(PAD_MD, PAD_MD, PAD_MD, PAD_MD)
        v.setSpacing(PAD_MD)
        v.addWidget(QLabel("Select a ticket to recall (double-click or OK):"))
        self._list = QListWidget()
        for i, t in enumerate(self._tickets):
            self._list.addItem(t.get("summary", f"Ticket {i + 1}"))
        self._list.itemDoubleClicked.connect(self._ok)
        if self._tickets:
            self._list.setCurrentRow(0)
        v.addWidget(self._list, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        style_dialog_button_box(bb, ok_icon="fa5s.check", cancel_icon="fa5s.times")
        v.addWidget(bb)

    def _ok(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            info_message(self, "Parked sales", "Select a parked sale.")
            return
        self.result = int(row)
        self.accept()


class ProcessReturnDialogQt(QDialog):
    """Find an invoice and return some or all line quantities; records a credit memo."""

    def __init__(self, parent, sales_service, main_window):
        super().__init__(parent)
        self._sales = sales_service
        self._main = main_window
        self._sale: dict | None = None
        self.memo: dict | None = None
        self._spin_by_si: dict[int, QDoubleSpinBox] = {}

        self.setWindowTitle("Process return / refund")
        self.resize(720, 420)
        v = QVBoxLayout(self)
        v.setContentsMargins(PAD_MD, PAD_MD, PAD_MD, PAD_MD)
        v.setSpacing(PAD_MD)

        row = QHBoxLayout()
        row.setSpacing(PAD_SM)
        row.addWidget(QLabel("Invoice #"))
        self._inv = QLineEdit()
        self._inv.setPlaceholderText("e.g. INV-2026-04-11-00001")
        row.addWidget(self._inv, 1)
        fb = QPushButton("Find sale")
        fb.setCursor(Qt.PointingHandCursor)
        fb.clicked.connect(self._find_sale)
        set_button_icon(fb, "fa5s.search")
        row.addWidget(fb)
        v.addLayout(row)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Product", "Code", "Sold", "Can return", "Return qty"]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        v.addWidget(self._table, 1)

        pay = QHBoxLayout()
        pay.setSpacing(PAD_SM)
        pay.addWidget(QLabel("Refund as:"))
        self._cash = QRadioButton("Cash")
        self._mobile = QRadioButton("Mobile")
        self._cash.setChecked(True)
        self._pay_group = QButtonGroup(self)
        self._pay_group.addButton(self._cash)
        self._pay_group.addButton(self._mobile)
        pay.addWidget(self._cash)
        pay.addWidget(self._mobile)
        pay.addStretch(1)
        v.addLayout(pay)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Process return")
        style_dialog_button_box(
            bb,
            ok_icon="fa5s.check-circle",
            cancel_icon="fa5s.times",
            ok_primary=True,
        )
        bb.accepted.connect(self._submit)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _find_sale(self) -> None:
        raw = self._inv.text().strip()
        if not raw:
            warning_message(self, "Return", "Enter an invoice number.")
            return
        sale = self._sales.find_sale_by_invoice(raw)
        if not sale:
            warning_message(self, "Return", "No sale found for that invoice number.")
            self._sale = None
            self._table.setRowCount(0)
            self._spin_by_si.clear()
            return
        self._sale = sale
        self._inv.setText(str(sale.get("invoice_number") or raw))
        returned = self._sales.returned_qty_by_sale_item(int(sale["id"]))
        items = sale.get("items") or []
        self._table.setRowCount(0)
        self._spin_by_si.clear()
        for it in items:
            si_id = int(it["id"])
            orig = float(it.get("quantity") or 0)
            already = float(returned.get(si_id, 0.0))
            remaining = max(0.0, orig - already)
            r = self._table.rowCount()
            self._table.insertRow(r)
            for c, val in enumerate(
                (
                    (it.get("name") or "")[:60],
                    (it.get("code") or "")[:24],
                    f"{orig:g}",
                    f"{remaining:g}",
                )
            ):
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                self._table.setItem(r, c, cell)
            spin = QDoubleSpinBox()
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin.setDecimals(2)
            spin.setRange(0.0, max(0.0, remaining))
            spin.setSingleStep(1.0)
            spin.setValue(0.0)
            spin.setMinimumWidth(100)
            self._table.setCellWidget(r, 4, spin)
            self._spin_by_si[si_id] = spin

    def _submit(self) -> None:
        if not self._sale:
            warning_message(self, "Return", "Find a sale first.")
            return
        lines: list[dict] = []
        for si_id, spin in self._spin_by_si.items():
            q = float(spin.value())
            if q > 1e-9:
                lines.append({"sale_item_id": si_id, "quantity": q})
        if not lines:
            warning_message(self, "Return", "Enter a return quantity on at least one line.")
            return
        method = "CASH" if self._cash.isChecked() else "MOBILE"
        try:
            self.memo = self._sales.record_return(
                int(self._sale["id"]),
                lines,
                {
                    "method": method,
                    "cashier_name": cashier_display_name(getattr(self._main, "current_user", None)),
                },
            )
        except ValueError as e:
            warning_message(self, "Return", str(e))
            return
        except Exception as e:
            warning_message(self, "Return", f"Could not record return: {e}")
            return
        self.accept()


class CreditMemoPreviewDialogQt(QDialog):
    def __init__(self, parent, memo: dict):
        super().__init__(parent)
        self._memo = memo
        self.setWindowTitle("Credit memo recorded")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(460, 520)
        v = QVBoxLayout(self)
        v.setContentsMargins(PAD_MD, PAD_MD, PAD_MD, PAD_MD)
        v.setSpacing(PAD_MD)
        hint = QLabel(
            "Stock has been increased by the returned quantities. "
            "Print or save this credit memo for your records."
        )
        hint.setWordWrap(True)
        v.addWidget(hint)
        lp = ShopSettings().get_logo_path()
        if lp and Path(lp).is_file():
            pix = QPixmap(lp)
            if not pix.isNull():
                logo_lab = QLabel()
                logo_lab.setPixmap(
                    pix.scaled(
                        160,
                        160,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                logo_lab.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                v.addWidget(logo_lab)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(format_credit_memo_plaintext(memo))
        v.addWidget(text, 1)

        row = QHBoxLayout()
        row.setSpacing(PAD_SM)
        print_btn = QPushButton("Print", clicked=self._do_print)
        save_btn = QPushButton("Save copy", clicked=self._do_save)
        done_btn = QPushButton("Done", clicked=self._on_done)
        done_btn.setObjectName("primary")
        set_button_icon(print_btn, "fa5s.print")
        set_button_icon(save_btn, "fa5s.save")
        set_button_icon(done_btn, "fa5s.check-circle")
        row.addWidget(print_btn)
        row.addWidget(save_btn)
        row.addStretch(1)
        row.addWidget(done_btn)
        v.addLayout(row)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def _on_done(self) -> None:
        ok, msg = archive_credit_memo_file(self._memo)
        if not ok:
            warning_message(self, "Credit memo not saved", msg)
        self.accept()

    def _do_print(self) -> None:
        ok, msg = print_credit_memo(self._memo)
        info_message(self, "Print" if ok else "Print failed", msg)

    def _do_save(self) -> None:
        ok, msg = archive_credit_memo_file(self._memo)
        info_message(self, "Saved" if ok else "Save failed", msg)
