"""Qt dialogs mirroring Tk PickProduct / Receipt / Recall flows."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QShowEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.receipt_output import archive_receipt_file, format_receipt_plaintext, print_receipt
from app.services.shop_settings import ShopSettings
from app.ui_qt.helpers_qt import format_money, info_message


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
        row = QHBoxLayout()
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
        v.addWidget(bb)

    def _apply_filter(self) -> None:
        q = self._filter_edit.text().strip().lower()
        if not q:
            self._filtered = list(self._all_products)
        else:
            self._filtered = [
                p
                for p in self._all_products
                if q in (p.get("name") or "").lower() or q in (p.get("code") or "").lower()
            ]
        self._populate_listbox()

    def _populate_listbox(self) -> None:
        self._list.clear()
        for p in self._filtered:
            line = f"{p.get('name', '')} — {p.get('code', '')} — {format_money(float(p.get('selling_price', 0)))}"
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
        self.setWindowTitle(f"Period summary · {start_date} — {end_date}")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(420, 480)
        v = QVBoxLayout(self)
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
        v.addWidget(QPushButton("Done", clicked=self.accept))

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
        hint = QLabel(
            "Print a receipt for the customer or save a record file (archived in this shop's receipts folder)."
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
        row.addWidget(QPushButton("Print receipt", clicked=self._do_print))
        row.addWidget(QPushButton("Save record", clicked=self._do_save))
        row.addStretch(1)
        row.addWidget(QPushButton("Done", clicked=self.accept))
        v.addLayout(row)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

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
        v.addWidget(bb)

    def _ok(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            info_message(self, "Parked sales", "Select a parked sale.")
            return
        self.result = int(row)
        self.accept()
