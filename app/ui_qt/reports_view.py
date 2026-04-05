"""Reports & CSV exports — PySide6."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import PAD_MD
from app.services.product_service import ProductService
from app.services.reports_service import ReportsService, format_sales_calendar_day
from app.services.shop_settings import get_display_shop_name

from app.ui_qt.helpers_qt import format_money, info_message, warning_message


def _first_of_month() -> str:
    t = date.today()
    return t.replace(day=1).isoformat()


def _today() -> str:
    return date.today().isoformat()


def _seven_days_ago() -> str:
    return (date.today() - timedelta(days=6)).isoformat()


class ReportsView(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._svc = ReportsService()
        self._products = ProductService()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(PAD_MD)

        t = QLabel("Reports & analytics")
        t.setObjectName("title")
        root.addWidget(t)
        sub = QLabel("Set an inclusive date range (YYYY-MM-DD), apply, then browse tabs. CSV exports are UTF-8.")
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        root.addWidget(sub)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("From"))
        self._start = QLineEdit(_first_of_month())
        self._start.setFixedWidth(120)
        bar.addWidget(self._start)
        bar.addWidget(QLabel("To"))
        self._end = QLineEdit(_today())
        self._end.setFixedWidth(120)
        bar.addWidget(self._end)
        ap = QPushButton("Apply range")
        ap.setObjectName("primary")
        ap.setCursor(Qt.PointingHandCursor)
        ap.clicked.connect(self.refresh)
        bar.addWidget(ap)
        m = QPushButton("This month")
        m.setCursor(Qt.PointingHandCursor)
        m.clicked.connect(self._this_month)
        bar.addWidget(m)
        w = QPushButton("Last 7 days")
        w.setCursor(Qt.PointingHandCursor)
        w.clicked.connect(self._last_7)
        bar.addWidget(w)
        bar.addStretch(1)
        root.addLayout(bar)

        self._err = QLabel("")
        self._err.setObjectName("errorText")
        root.addWidget(self._err)

        tabs = QTabWidget()
        root.addWidget(tabs, 1)

        # Summary
        sum_w = QWidget()
        sum_l = QGridLayout(sum_w)
        sum_l.setSpacing(8)
        self._sum_labels: dict[str, QLabel] = {}
        specs = [
            ("invoice_count", "Invoices"),
            ("gross_total", "Gross sales"),
            ("discount_total", "Discounts"),
            ("subtotal_total", "Subtotal (pre-discount)"),
            ("avg_ticket", "Avg ticket (gross)"),
        ]
        for i, (key, title) in enumerate(specs):
            sum_l.addWidget(QLabel(f"<b>{title}</b>"), i, 0)
            lb = QLabel("—")
            self._sum_labels[key] = lb
            sum_l.addWidget(lb, i, 1)
        tabs.addTab(sum_w, "Summary")

        day_w = QWidget()
        day_l = QVBoxLayout(day_w)
        day_l.setContentsMargins(0, 0, 0, 0)
        self._daily_sales_title = QLabel("")
        self._daily_sales_title.setObjectName("pageSubtitle")
        self._daily_sales_title.setWordWrap(True)
        day_l.addWidget(self._daily_sales_title)
        self._day_table = QTableWidget(0, 3)
        self._day_table.setHorizontalHeaderLabels(["Calendar day", "Invoices", "Gross"])
        self._stretch_col(self._day_table, 0)
        day_l.addWidget(self._day_table, 1)
        tabs.addTab(day_w, "Daily sales")

        self._pay_table = QTableWidget(0, 3)
        self._pay_table.setHorizontalHeaderLabels(["Method", "Invoices", "Gross"])
        self._stretch_col(self._pay_table, 0)
        tabs.addTab(self._pay_table, "Payment mix")

        self._top_table = QTableWidget(0, 4)
        self._top_table.setHorizontalHeaderLabels(["SKU", "Product", "Qty sold", "Revenue"])
        self._stretch_col(self._top_table, 1)
        tabs.addTab(self._top_table, "Top products")

        inv_w = QWidget()
        inv_v = QVBoxLayout(inv_w)
        self._inv_grid = QGridLayout()
        self._inv_labels: dict[str, QLabel] = {}
        inv_specs = [
            ("skus", "Active SKUs"),
            ("units", "Units on hand"),
            ("retail_value", "Retail value"),
            ("cost_value", "Cost value"),
            ("margin_hint", "Retail − cost"),
        ]
        for i, (key, title) in enumerate(inv_specs):
            self._inv_grid.addWidget(QLabel(f"<b>{title}</b>"), i, 0)
            lb = QLabel("—")
            self._inv_labels[key] = lb
            self._inv_grid.addWidget(lb, i, 1)
        inv_v.addLayout(self._inv_grid)
        inv_v.addWidget(QLabel("<b>Low stock (≤ min level)</b>"))
        self._low_table = QTableWidget(0, 4)
        self._low_table.setHorizontalHeaderLabels(["SKU", "Product", "Stock", "Min"])
        self._stretch_col(self._low_table, 1)
        inv_v.addWidget(self._low_table, 1)
        tabs.addTab(inv_w, "Inventory")

        self._pur_table = QTableWidget(0, 7)
        self._pur_table.setHorizontalHeaderLabels(
            ["Reference", "Received", "Supplier", "Phone", "Email", "Lines", "Value"]
        )
        self._stretch_col(self._pur_table, 4)
        tabs.addTab(self._pur_table, "Purchases")

        ex_w = QWidget()
        ex_v = QVBoxLayout(ex_w)
        ex_v.addWidget(QLabel("Uses the date range above."))
        b1 = QPushButton("Export sales (one row per invoice)")
        b1.setCursor(Qt.PointingHandCursor)
        b1.clicked.connect(self._export_sales)
        ex_v.addWidget(b1)
        b2 = QPushButton("Export sale lines (one row per line item)")
        b2.setCursor(Qt.PointingHandCursor)
        b2.clicked.connect(self._export_lines)
        ex_v.addWidget(b2)
        ex_v.addStretch(1)
        tabs.addTab(ex_w, "Export CSV")

    @staticmethod
    def _stretch_col(table: QTableWidget, col: int) -> None:
        table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

    def _this_month(self) -> None:
        self._start.setText(_first_of_month())
        self._end.setText(_today())
        self.refresh()

    def _last_7(self) -> None:
        self._start.setText(_seven_days_ago())
        self._end.setText(_today())
        self.refresh()

    def show_invoice_from_global_search(self, invoice_query: str) -> bool:
        """If a sale exists for this invoice number, narrow the report range to that day and notify."""
        sale = self._svc.get_sale_by_invoice_number(invoice_query)
        if not sale:
            return False
        raw_date = str(sale.get("sale_date") or "").strip()
        day = raw_date[:10]
        if len(day) != 10:
            day = _today()
        self._start.setText(day)
        self._end.setText(day)
        self.refresh()
        gross = float(sale.get("total_amount") or 0)
        pm = (sale.get("payment_method") or "").strip() or "—"
        info_message(
            self.window(),
            "Invoice found",
            f"{sale.get('invoice_number')}\n{day} · {format_money(gross)} · {pm}",
        )
        return True

    def _range(self) -> tuple[str, str]:
        return self._start.text().strip(), self._end.text().strip()

    def _fill_table(self, table: QTableWidget, rows: list[tuple]) -> None:
        table.setRowCount(0)
        for vals in rows:
            r = table.rowCount()
            table.insertRow(r)
            for c, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                table.setItem(r, c, it)

    def refresh(self) -> None:
        self._err.setText("")
        start, end = self._range()
        try:
            summary = self._svc.sales_summary(start, end)
        except ValueError as e:
            self._err.setText(str(e))
            return

        self._sum_labels["invoice_count"].setText(str(summary["invoice_count"]))
        self._sum_labels["gross_total"].setText(format_money(summary["gross_total"]))
        self._sum_labels["discount_total"].setText(format_money(summary["discount_total"]))
        self._sum_labels["subtotal_total"].setText(format_money(summary["subtotal_total"]))
        self._sum_labels["avg_ticket"].setText(format_money(summary["avg_ticket"]))

        self._daily_sales_title.setText(f"Daily sales — {get_display_shop_name()}")

        try:
            day_rows = [
                (
                    format_sales_calendar_day(r.get("day")),
                    r.get("invoices"),
                    format_money(float(r.get("gross_total") or 0)),
                )
                for r in self._svc.sales_by_day(start, end)
            ]
            pay_rows = [
                (
                    r.get("method"),
                    r.get("invoices"),
                    format_money(float(r.get("gross_total") or 0)),
                )
                for r in self._svc.sales_by_payment_method(start, end)
            ]
            top_rows = []
            for r in self._svc.top_products_by_revenue(start, end, 40):
                q = float(r.get("qty_sold") or 0)
                qv = f"{q:g}" if q == int(q) else f"{q:.2f}"
                top_rows.append(
                    (r.get("code"), r.get("name"), qv, format_money(float(r.get("revenue") or 0))),
                )
            pur_rows = [
                (
                    r.get("reference"),
                    str(r.get("received_at") or "")[:19],
                    (r.get("supplier_name") or "")[:40],
                    (r.get("supplier_phone") or "")[:32],
                    (r.get("supplier_email") or "")[:40],
                    int(r.get("line_count") or 0),
                    format_money(float(r.get("total_value") or 0)),
                )
                for r in self._svc.purchase_receipts_in_range(start, end)
            ]
        except ValueError as e:
            self._err.setText(str(e))
            return

        self._fill_table(self._day_table, day_rows)
        self._fill_table(self._pay_table, pay_rows)
        self._fill_table(self._top_table, top_rows)
        self._fill_table(self._pur_table, pur_rows)

        snap = self._svc.inventory_valuation_snapshot()
        self._inv_labels["skus"].setText(str(snap["skus"]))
        self._inv_labels["units"].setText(f"{snap['units']:,.2f}")
        self._inv_labels["retail_value"].setText(format_money(snap["retail_value"]))
        self._inv_labels["cost_value"].setText(format_money(snap["cost_value"]))
        self._inv_labels["margin_hint"].setText(format_money(snap["margin_hint"]))

        low_rows = []
        for p in self._products.get_low_stock()[:80]:
            low_rows.append(
                (
                    p.get("code"),
                    p.get("name"),
                    f"{float(p.get('quantity_in_stock') or 0):g}",
                    f"{float(p.get('minimum_stock_level') or 0):g}",
                )
            )
        self._fill_table(self._low_table, low_rows)

    def _export_sales(self) -> None:
        start, end = self._range()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export sales",
            f"sales_{start}_{end}.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            out = self._svc.export_sales_csv(path, start, end)
        except ValueError as e:
            warning_message(self.window(), "Export", str(e))
            return
        info_message(self.window(), "Export", f"Saved:\n{out}")

    def _export_lines(self) -> None:
        start, end = self._range()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export sale lines",
            f"sale_lines_{start}_{end}.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            out = self._svc.export_sale_lines_csv(path, start, end)
        except ValueError as e:
            warning_message(self.window(), "Export", str(e))
            return
        info_message(self.window(), "Export", f"Saved:\n{out}")
