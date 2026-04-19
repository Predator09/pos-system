"""Reports & CSV exports — PySide6."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import PAD_LG, PAD_MD, PAD_SM
from app.ui.date_display import format_iso_date_as_display, parse_date_input
from app.services.product_service import ProductService
from app.services.purchase_service import PurchaseService
from app.services.reports_service import ReportsService, format_report_period_title, format_sales_calendar_day
from app.services.sales_service import SalesService
from app.services.shop_settings import get_display_shop_name
from app.ui.helpers import format_purchase_timestamp

from app.ui_qt.dialogs_qt import PurchaseReceiptDetailDialogQt, ReceiptPreviewDialogQt
from app.ui_qt.helpers_qt import format_money, info_message, warning_message
from app.ui_qt.icon_utils import set_button_icon

_TOP_SELLERS_LIMIT = 15


def _first_of_month() -> str:
    t = date.today()
    return format_iso_date_as_display(t.replace(day=1).isoformat())


def _today() -> str:
    return format_iso_date_as_display(date.today().isoformat())


def _seven_days_ago() -> str:
    return format_iso_date_as_display((date.today() - timedelta(days=6)).isoformat())


class ReportsView(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._svc = ReportsService()
        self._sales = SalesService()
        self._products = ProductService()
        self._purchases = PurchaseService()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(PAD_MD)

        t = QLabel("Reports")
        t.setObjectName("title")
        root.addWidget(t)
        sub = QLabel(
            "Daily report: one calendar day or a date range (inclusive), dates as DD-MM-YYYY. "
            "Stock & CSV on tab 2; sales receipts by day on tab 3."
        )
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        root.addWidget(sub)

        bar = QGridLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setHorizontalSpacing(PAD_SM)
        bar.setVerticalSpacing(PAD_SM)
        bar.addWidget(QLabel("From"), 0, 0)
        self._start = QLineEdit(_today())
        self._start.setFixedWidth(110)
        self._start.setPlaceholderText("DD-MM-YYYY")
        bar.addWidget(self._start, 0, 1)
        bar.addWidget(QLabel("To"), 0, 2)
        self._end = QLineEdit(_today())
        self._end.setFixedWidth(110)
        self._end.setPlaceholderText("DD-MM-YYYY")
        self._end.setFixedWidth(120)
        bar.addWidget(self._end, 0, 3)
        td = QPushButton("Today")
        td.setCursor(Qt.PointingHandCursor)
        td.clicked.connect(self._today_range)
        set_button_icon(td, "fa5s.calendar-day")
        bar.addWidget(td, 0, 4)
        ap = QPushButton("Apply")
        ap.setObjectName("primary")
        ap.setCursor(Qt.PointingHandCursor)
        ap.clicked.connect(self.refresh)
        set_button_icon(ap, "fa5s.check")
        bar.addWidget(ap, 0, 5)
        w = QPushButton("Last 7 days")
        w.setCursor(Qt.PointingHandCursor)
        w.clicked.connect(self._last_7)
        set_button_icon(w, "fa5s.calendar-week")
        bar.addWidget(w, 0, 6)
        m = QPushButton("This month")
        m.setCursor(Qt.PointingHandCursor)
        m.clicked.connect(self._this_month)
        set_button_icon(m, "fa5s.calendar-alt")
        bar.addWidget(m, 0, 7)
        bar.setColumnStretch(8, 1)

        self._err = QLabel("")
        self._err.setObjectName("errorText")

        tabs = QTabWidget()

        body_card = QFrame()
        body_card.setObjectName("card")
        body_l = QVBoxLayout(body_card)
        body_l.setContentsMargins(PAD_MD, PAD_MD, PAD_MD, PAD_MD)
        body_l.setSpacing(PAD_MD)
        body_l.addLayout(bar)
        body_l.addWidget(self._err)
        body_l.addWidget(tabs, 1)
        root.addWidget(body_card, 1)

        # --- Daily report (scrollable) ---
        daily_outer = QWidget()
        daily_outer_l = QVBoxLayout(daily_outer)
        daily_outer_l.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        daily_inner = QWidget()
        daily_l = QVBoxLayout(daily_inner)
        daily_l.setContentsMargins(0, 0, 0, 0)
        daily_l.setSpacing(PAD_MD)

        self._period_title = QLabel("")
        self._period_title.setObjectName("pageSubtitle")
        self._period_title.setWordWrap(True)
        daily_l.addWidget(self._period_title)
        self._period_sub = QLabel("")
        self._period_sub.setObjectName("muted")
        self._period_sub.setWordWrap(True)
        daily_l.addWidget(self._period_sub)

        kpi = QGridLayout()
        kpi.setHorizontalSpacing(PAD_MD)
        kpi.setVerticalSpacing(PAD_MD)
        self._sum_labels: dict[str, QLabel] = {}
        specs = [
            ("invoice_count", "Invoices"),
            ("gross_total", "Net sales"),
            ("refund_total", "Refunds"),
            ("avg_ticket", "Avg ticket (net)"),
            ("discount_total", "Discounts"),
            ("subtotal_total", "Subtotal (before discounts)"),
        ]
        for i, (key, title) in enumerate(specs):
            col = QVBoxLayout()
            col.setSpacing(PAD_SM)
            col.addWidget(QLabel(f"<span style='color:gray'>{title}</span>"))
            lb = QLabel("—")
            lb.setStyleSheet("font-size: 16px; font-weight: bold;")
            col.addWidget(lb)
            col.addStretch(0)
            wk = QWidget()
            wk.setLayout(col)
            kpi.addWidget(wk, i // 3, i % 3)
            self._sum_labels[key] = lb
        daily_l.addLayout(kpi)

        self._day_block = QWidget()
        day_block_l = QVBoxLayout(self._day_block)
        day_block_l.setContentsMargins(0, 0, 0, 0)
        day_block_l.setSpacing(PAD_SM)
        day_block_l.addWidget(QLabel("<b>Sales by calendar day</b>"))
        self._day_table = QTableWidget(0, 3)
        self._day_table.setHorizontalHeaderLabels(["Day", "Invoices", "Net"])
        self._stretch_col(self._day_table, 0)
        self._day_table.setMaximumHeight(280)
        day_block_l.addWidget(self._day_table)
        self._day_block.setVisible(False)
        daily_l.addWidget(self._day_block)

        daily_l.addWidget(QLabel("<b>Payment mix</b>"))
        self._pay_table = QTableWidget(0, 3)
        self._pay_table.setHorizontalHeaderLabels(["Method", "Invoices", "Net"])
        self._stretch_col(self._pay_table, 0)
        self._pay_table.setMaximumHeight(220)
        daily_l.addWidget(self._pay_table)

        daily_l.addWidget(QLabel("<b>Top sellers (by revenue)</b>"))
        self._top_table = QTableWidget(0, 4)
        self._top_table.setHorizontalHeaderLabels(["PC", "Product", "Qty", "Revenue"])
        self._stretch_col(self._top_table, 1)
        self._top_table.setMinimumHeight(200)
        daily_l.addWidget(self._top_table, 1)

        scroll.setWidget(daily_inner)
        daily_outer_l.addWidget(scroll)
        tabs.addTab(daily_outer, "Daily report")

        # --- Stock & export ---
        more_outer = QWidget()
        more_outer_l = QVBoxLayout(more_outer)
        more_outer_l.setContentsMargins(0, 0, 0, 0)
        more_scroll = QScrollArea()
        more_scroll.setWidgetResizable(True)
        more_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        more_inner = QWidget()
        more_l = QVBoxLayout(more_inner)
        more_l.setContentsMargins(0, 0, 0, 0)
        more_l.setSpacing(PAD_MD)

        more_l.addWidget(
            QLabel("<span style='color:gray'>Inventory snapshot (always current — not limited by the date range).</span>")
        )
        self._inv_grid = QGridLayout()
        self._inv_labels: dict[str, QLabel] = {}
        inv_specs = [
            ("skus", "Active products"),
            ("units", "Units on hand"),
            ("retail_value", "Retail value"),
            ("cost_value", "Cost value"),
            ("profit", "Profit"),
        ]
        for i, (key, title) in enumerate(inv_specs):
            self._inv_grid.addWidget(QLabel(f"<b>{title}</b>"), i, 0)
            lb = QLabel("—")
            self._inv_labels[key] = lb
            self._inv_grid.addWidget(lb, i, 1)
        more_l.addLayout(self._inv_grid)

        more_l.addWidget(QLabel("<b>Low stock (≤ min)</b>"))
        self._low_table = QTableWidget(0, 4)
        self._low_table.setHorizontalHeaderLabels(["PC", "Product", "Stock", "Min"])
        self._stretch_col(self._low_table, 1)
        self._low_table.setMaximumHeight(260)
        more_l.addWidget(self._low_table)

        more_l.addWidget(
            QLabel(
                "<b>Purchase receipts in range</b> "
                "<span style='color:gray'>— double-click a row for line details.</span>"
            )
        )
        self._pur_table = QTableWidget(0, 7)
        self._pur_table.setHorizontalHeaderLabels(
            ["Ref.", "Date & time", "Supplier", "Phone", "Email", "Lines", "Value"]
        )
        self._pur_table.setColumnWidth(1, 168)
        self._stretch_col(self._pur_table, 4)
        self._pur_table.setMaximumHeight(260)
        self._pur_table.doubleClicked.connect(self._on_purchase_receipt_double_click)
        more_l.addWidget(self._pur_table)

        more_l.addWidget(QLabel("<b>Export CSV</b>"))
        b1 = QPushButton("Sales — one row per invoice")
        b1.setCursor(Qt.PointingHandCursor)
        b1.clicked.connect(self._export_sales)
        set_button_icon(b1, "fa5s.file-invoice-dollar")
        more_l.addWidget(b1)
        b2 = QPushButton("Sale lines — one row per line item")
        b2.setCursor(Qt.PointingHandCursor)
        b2.clicked.connect(self._export_lines)
        set_button_icon(b2, "fa5s.file-csv")
        more_l.addWidget(b2)
        more_l.addStretch(1)

        more_scroll.setWidget(more_inner)
        more_outer_l.addWidget(more_scroll)
        tabs.addTab(more_outer, "Stock & export")

        # --- Sales receipts by day ---
        rcpt_outer = QWidget()
        rcpt_outer_l = QVBoxLayout(rcpt_outer)
        rcpt_outer_l.setContentsMargins(0, 0, 0, 0)
        rcpt_outer_l.addWidget(
            QLabel(
                "<span style='color:gray'>Every sale in the date range above, grouped by calendar day (newest first). "
                "Double-click an invoice row, or select it and click Preview receipt.</span>"
            )
        )
        rcpt_btn_row = QHBoxLayout()
        self._rcpt_preview_btn = QPushButton("Preview receipt")
        self._rcpt_preview_btn.setCursor(Qt.PointingHandCursor)
        self._rcpt_preview_btn.setObjectName("ghost")
        self._rcpt_preview_btn.clicked.connect(self._preview_receipt_from_tree)
        set_button_icon(self._rcpt_preview_btn, "fa5s.receipt")
        rcpt_btn_row.addWidget(self._rcpt_preview_btn)
        rcpt_btn_row.addStretch(1)
        rcpt_outer_l.addLayout(rcpt_btn_row)
        self._rcpt_tree = QTreeWidget()
        self._rcpt_tree.setHeaderLabels(["Day / invoice", "Time", "Payment", "Customer", "Staff", "Total"])
        self._rcpt_tree.setColumnWidth(0, 200)
        self._rcpt_tree.setColumnWidth(1, 88)
        self._rcpt_tree.setColumnWidth(2, 100)
        self._rcpt_tree.setColumnWidth(3, 140)
        self._rcpt_tree.setColumnWidth(4, 120)
        self._rcpt_tree.header().setStretchLastSection(True)
        self._rcpt_tree.itemDoubleClicked.connect(self._on_receipt_tree_double_click)
        rcpt_outer_l.addWidget(self._rcpt_tree, 1)
        tabs.addTab(rcpt_outer, "Sales receipts")

    @staticmethod
    def _stretch_col(table: QTableWidget, col: int) -> None:
        table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

    def _today_range(self) -> None:
        self._start.setText(_today())
        self._end.setText(_today())
        self.refresh()

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
        day_iso = raw_date[:10]
        if len(day_iso) != 10 or day_iso[4] != "-":
            day_iso = date.today().isoformat()
        day_disp = format_iso_date_as_display(day_iso)
        self._start.setText(day_disp)
        self._end.setText(day_disp)
        self.refresh()
        gross = float(sale.get("total_amount") or 0)
        pm = (sale.get("payment_method") or "").strip() or "—"
        info_message(
            self.window(),
            "Invoice found",
            f"{sale.get('invoice_number')}\n{day_disp} · {format_money(gross)} · {pm}",
        )
        return True

    def _range(self) -> tuple[str, str]:
        return self._start.text().strip(), self._end.text().strip()

    def _sale_id_from_receipt_item(self, item: QTreeWidgetItem | None) -> int | None:
        if item is None:
            return None
        raw = item.data(0, Qt.ItemDataRole.UserRole)
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _open_receipt_preview(self, sale_id: int) -> None:
        full = self._sales.get_sale(sale_id)
        if not full:
            warning_message(self.window(), "Receipt", "That sale could not be loaded.")
            return
        ReceiptPreviewDialogQt(self.window(), full).exec()

    def _on_receipt_tree_double_click(self, item: QTreeWidgetItem, _column: int) -> None:
        sid = self._sale_id_from_receipt_item(item)
        if sid is not None:
            self._open_receipt_preview(sid)

    def _preview_receipt_from_tree(self) -> None:
        item = self._rcpt_tree.currentItem()
        sid = self._sale_id_from_receipt_item(item)
        if sid is None:
            info_message(
                self.window(),
                "Preview receipt",
                "Select an invoice row under a day (not the day summary row), then click Preview receipt or double-click the row.",
            )
            return
        self._open_receipt_preview(sid)

    def _fill_table(self, table: QTableWidget, rows: list[tuple]) -> None:
        table.setRowCount(0)
        for vals in rows:
            r = table.rowCount()
            table.insertRow(r)
            for c, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                table.setItem(r, c, it)

    def _on_purchase_receipt_double_click(self) -> None:
        r = self._pur_table.currentRow()
        if r < 0:
            return
        it = self._pur_table.item(r, 0)
        if it is None:
            return
        rid = it.data(Qt.ItemDataRole.UserRole)
        if rid is None:
            return
        PurchaseReceiptDetailDialogQt(self.window(), self._purchases, int(rid)).exec()

    def refresh(self) -> None:
        self._err.setText("")
        start_raw, end_raw = self._range()
        try:
            start = parse_date_input(start_raw)
            end = parse_date_input(end_raw)
        except ValueError as e:
            self._err.setText(str(e))
            return
        try:
            summary = self._svc.sales_summary(start, end)
        except ValueError as e:
            self._err.setText(str(e))
            return

        shop = get_display_shop_name()
        self._period_title.setText(format_report_period_title(start, end))
        if start == end:
            self._period_sub.setText(f"{shop} · Figures are for this single day.")
            self._day_block.setVisible(False)
        else:
            self._period_sub.setText(f"{shop} · Range totals below; split by day in the table.")
            self._day_block.setVisible(True)

        self._sum_labels["invoice_count"].setText(str(summary["invoice_count"]))
        self._sum_labels["gross_total"].setText(format_money(summary["gross_total"]))
        self._sum_labels["refund_total"].setText(format_money(summary["refund_total"]))
        self._sum_labels["discount_total"].setText(format_money(summary["discount_total"]))
        self._sum_labels["subtotal_total"].setText(format_money(summary["subtotal_total"]))
        self._sum_labels["avg_ticket"].setText(format_money(summary["avg_ticket"]))

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
            for r in self._svc.top_products_by_revenue(start, end, _TOP_SELLERS_LIMIT):
                q = float(r.get("qty_sold") or 0)
                qv = f"{q:g}" if q == int(q) else f"{q:.2f}"
                top_rows.append(
                    (r.get("code"), r.get("name"), qv, format_money(float(r.get("revenue") or 0))),
                )
            pur_data = self._svc.purchase_receipts_in_range(start, end)
            pur_rows = [
                (
                    r.get("reference"),
                    format_purchase_timestamp(r.get("received_at") or r.get("created_at")),
                    (r.get("supplier_name") or "")[:40],
                    (r.get("supplier_phone") or "")[:32],
                    (r.get("supplier_email") or "")[:40],
                    int(r.get("line_count") or 0),
                    format_money(float(r.get("total_value") or 0)),
                )
                for r in pur_data
            ]
            rcpt_groups = self._svc.sales_receipts_grouped_by_day(start, end)
        except ValueError as e:
            self._err.setText(str(e))
            return

        self._fill_table(self._day_table, day_rows)
        self._fill_table(self._pay_table, pay_rows)
        self._fill_table(self._top_table, top_rows)
        self._fill_table(self._pur_table, pur_rows)
        for i, pr in enumerate(pur_data):
            cell = self._pur_table.item(i, 0)
            if cell is not None:
                cell.setData(Qt.ItemDataRole.UserRole, int(pr["id"]))

        self._rcpt_tree.clear()
        for grp in rcpt_groups:
            day_key = grp.get("day") or ""
            receipts = grp.get("receipts") or []
            n = len(receipts)
            day_gross = sum(float(x.get("total_amount") or 0) for x in receipts)
            count_lbl = f"{n} receipt" + ("" if n == 1 else "s")
            parent = QTreeWidgetItem(
                [
                    format_sales_calendar_day(day_key),
                    count_lbl,
                    "—",
                    "—",
                    "—",
                    format_money(day_gross),
                ]
            )
            self._rcpt_tree.addTopLevelItem(parent)
            for r in receipts:
                ts = format_purchase_timestamp(r.get("sale_date"))
                time_part = ts[11:19] if len(ts) >= 19 and ts[10] == " " else ts
                inv = (r.get("invoice_number") or "").strip() or "—"
                cust = ((r.get("customer_name") or "").strip() or "—")[:40]
                pm = (r.get("payment_method") or "").strip() or "—"
                staff = ((r.get("cashier_name") or "").strip() or "—")[:36]
                child = QTreeWidgetItem(
                    [
                        inv,
                        time_part,
                        pm,
                        cust,
                        staff,
                        format_money(float(r.get("total_amount") or 0)),
                    ]
                )
                sid = r.get("id")
                if sid is not None:
                    child.setData(0, Qt.ItemDataRole.UserRole, int(sid))
                parent.addChild(child)
            parent.setExpanded(True)

        snap = self._svc.inventory_valuation_snapshot()
        self._inv_labels["skus"].setText(str(snap["skus"]))
        self._inv_labels["units"].setText(f"{snap['units']:,.2f}")
        self._inv_labels["retail_value"].setText(format_money(snap["retail_value"]))
        self._inv_labels["cost_value"].setText(format_money(snap["cost_value"]))
        self._inv_labels["profit"].setText(format_money(snap["profit"]))

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
        start_raw, end_raw = self._range()
        try:
            start = parse_date_input(start_raw)
            end = parse_date_input(end_raw)
        except ValueError as e:
            warning_message(self.window(), "Export", str(e))
            return
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
        start_raw, end_raw = self._range()
        try:
            start = parse_date_input(start_raw)
            end = parse_date_input(end_raw)
        except ValueError as e:
            warning_message(self.window(), "Export", str(e))
            return
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
