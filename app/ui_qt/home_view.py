"""Dashboard: same service calls and refresh logic as Tk HomeScreen; dashboard-style layout."""

from datetime import date, datetime, timedelta

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, PAD_LG, PAD_MD, VERSION
from app.services.shop_context import database_path
from app.services.shop_settings import get_display_shop_name
from app.database.connection import db
from app.services.app_settings import AppSettings
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService
from app.services.inventory_service import InventoryService
from app.services.receipt_output import format_period_sales_summary
from app.services.sales_service import SalesService
from app.ui.theme_tokens import TOKENS

from app.ui.helpers import home_welcome_detail_line, home_welcome_status_line
from app.ui_qt.dashboard_sales_chart import DashboardSalesChart
from app.ui_qt.helpers_qt import format_money, info_message, warning_message
from app.ui_qt.dialogs_qt import PeriodSalesSummaryDialogQt, ReceiptPreviewDialogQt
from app.ui_qt.manage_users_qt import ManageUsersDialogQt


class HomeView(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._sales = SalesService()
        self._inventory = InventoryService()
        self._backup = BackupService()

        self._overview_value: QLabel | None = None
        self._overview_delta: QLabel | None = None
        self._mini_invoices: QLabel | None = None
        self._mini_cash: QLabel | None = None
        self._mini_net: QLabel | None = None
        self._mini_skus: QLabel | None = None
        self._low_card: QFrame | None = None
        self._status_labels: dict[str, QLabel] = {}
        self._recent_inner: QWidget | None = None
        self._suppress_appearance_cb = False
        self._pill_group: QButtonGroup | None = None

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner.setObjectName("dashboardInner")
        root = QVBoxLayout(inner)
        root.setSpacing(PAD_MD)

        # Status strip
        strip = QFrame()
        strip.setObjectName("card")
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(16, 12, 16, 12)
        self._status_labels["db"] = QLabel("")
        self._status_labels["theme"] = QLabel("")
        self._status_labels["backup"] = QLabel("")
        for k in ("db", "theme", "backup"):
            sl.addWidget(self._status_labels[k])
            sl.addSpacing(PAD_LG)
        root.addWidget(strip)

        main_row = QHBoxLayout()
        main_row.setSpacing(16)

        # ---- Left column: sales overview + recent ----
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        overview = QFrame()
        overview.setObjectName("card")
        ov = QVBoxLayout(overview)
        ov.setContentsMargins(20, 18, 20, 18)
        ov.setSpacing(12)

        hdr = QHBoxLayout()
        oh = QLabel("Sales overview")
        oh.setObjectName("section")
        hdr.addWidget(oh)
        hdr.addStretch(1)
        self._range_combo = QComboBox()
        self._range_combo.addItems(["Today", "Yesterday", "This week"])
        self._range_combo.setMinimumWidth(160)
        self._range_combo.currentIndexChanged.connect(lambda _i: self.refresh())
        hdr.addWidget(self._range_combo)
        ov.addLayout(hdr)

        self._overview_value = QLabel("—")
        self._overview_value.setObjectName("heroMetric")
        ov.addWidget(self._overview_value)

        self._overview_delta = QLabel("")
        self._overview_delta.setObjectName("muted")
        ov.addWidget(self._overview_delta)

        pills = QHBoxLayout()
        pills.setSpacing(8)
        self._pill_group = QButtonGroup(self)
        self._pill_group.setExclusive(True)
        for i, cap in enumerate(("12 mo", "30 d", "7 d", "24 h")):
            pb = QPushButton(cap)
            pb.setCheckable(True)
            pb.setObjectName("pillTab")
            pb.setCursor(Qt.PointingHandCursor)
            if i == 3:
                pb.setChecked(True)
            self._pill_group.addButton(pb, i)
            pills.addWidget(pb)
        pills.addStretch(1)
        ov.addLayout(pills)
        self._pill_group.idClicked.connect(lambda _id: self.refresh())

        chart_hdr = QHBoxLayout()
        cpt = QLabel("Sales trend")
        cpt.setObjectName("chartPlaceholderTitle")
        chart_hdr.addWidget(cpt)
        chart_hdr.addStretch(1)
        sum_btn = QPushButton("Receipt-style summary")
        sum_btn.setObjectName("ghost")
        sum_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sum_btn.setToolTip("Open a receipt-style text summary for the selected period")
        sum_btn.clicked.connect(self._open_period_sales_summary)
        chart_hdr.addWidget(sum_btn)
        ov.addLayout(chart_hdr)
        self._sales_chart = DashboardSalesChart()
        self._sales_chart.setMinimumHeight(240)
        ov.addWidget(self._sales_chart, 1)

        left_col.addWidget(overview)

        recent_box = QFrame()
        recent_box.setObjectName("card")
        rl = QVBoxLayout(recent_box)
        rl.setContentsMargins(16, 14, 16, 14)
        rh = QLabel("Recent checkouts")
        rh.setObjectName("section")
        rl.addWidget(rh)
        rsub = QLabel("Last 5 sales · click a row to preview the receipt")
        rsub.setObjectName("muted")
        rsub.setWordWrap(True)
        rl.addWidget(rsub)
        self._recent_inner = QWidget()
        self._recent_layout = QVBoxLayout(self._recent_inner)
        self._recent_layout.setAlignment(Qt.AlignTop)
        rl.addWidget(self._recent_inner)
        left_col.addWidget(recent_box, 1)

        main_row.addLayout(left_col, 7)

        # ---- Right column: KPI mini cards + actions ----
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        def _mini_card(title_label: QLabel, value_label: QLabel) -> QFrame:
            f = QFrame()
            f.setObjectName("miniKpiCard")
            fl = QVBoxLayout(f)
            fl.setContentsMargins(16, 14, 16, 14)
            fl.setSpacing(6)
            title_label.setObjectName("miniKpiTitle")
            fl.addWidget(title_label)
            value_label.setObjectName("miniKpiValue")
            fl.addWidget(value_label)
            return f

        self._mini_inv_title = QLabel("Invoices (today)")
        self._mini_invoices = QLabel("—")
        right_col.addWidget(_mini_card(self._mini_inv_title, self._mini_invoices))

        self._mini_cash_title = QLabel("Cash (today)")
        self._mini_cash = QLabel("—")
        right_col.addWidget(_mini_card(self._mini_cash_title, self._mini_cash))

        self._mini_net_title = QLabel("Sales total (today)")
        self._mini_net = QLabel("—")
        right_col.addWidget(_mini_card(self._mini_net_title, self._mini_net))

        self._low_card = QFrame()
        self._low_card.setObjectName("card")
        ll = QVBoxLayout(self._low_card)
        ll.setContentsMargins(16, 14, 16, 14)
        donut = QFrame()
        donut.setObjectName("donutPlaceholder")
        donut.setFixedSize(120, 120)
        dl = QVBoxLayout(donut)
        dl.setAlignment(Qt.AlignCenter)
        self._mini_skus = QLabel("—")
        self._mini_skus.setObjectName("donutValue")
        dl.addWidget(self._mini_skus, alignment=Qt.AlignCenter)
        dcap = QLabel("Active SKUs")
        dcap.setObjectName("muted")
        dl.addWidget(dcap, alignment=Qt.AlignCenter)
        ll.addWidget(donut, alignment=Qt.AlignCenter)
        right_col.addWidget(self._low_card)

        low_hint = QLabel("Low stock alerts use the threshold under 10 units.")
        low_hint.setObjectName("muted")
        low_hint.setWordWrap(True)
        right_col.addWidget(low_hint)

        sess = QFrame()
        sess.setObjectName("card")
        se = QVBoxLayout(sess)
        se.setContentsMargins(16, 14, 16, 14)
        seh = QLabel("Session & preferences")
        seh.setObjectName("section")
        se.addWidget(seh)
        self._welcome_label = QLabel("")
        self._welcome_label.setObjectName("pageSubtitle")
        self._welcome_label.setWordWrap(True)
        se.addWidget(self._welcome_label)
        self._role_badge = QLabel("")
        self._role_badge.setObjectName("pillNeutral")
        se.addWidget(self._role_badge)
        row_dm = QHBoxLayout()
        row_dm.addWidget(QLabel("Dark mode"))
        self._appearance_check = QCheckBox()
        self._appearance_check.toggled.connect(self._on_appearance_toggle)
        row_dm.addWidget(self._appearance_check)
        row_dm.addStretch(1)
        se.addLayout(row_dm)
        self._app_info_inner = QWidget()
        self._app_info_form = QGridLayout(self._app_info_inner)
        se.addWidget(self._app_info_inner)
        right_col.addWidget(sess)

        foot = QHBoxLayout()
        foot.setSpacing(10)
        bu = QPushButton("Backup now", clicked=self._backup_now)
        bu.setObjectName("primary")
        bu.setCursor(Qt.PointingHandCursor)
        foot.addWidget(bu)
        self._manage_users_btn = QPushButton("Manage users", clicked=self._open_manage_users)
        self._manage_users_btn.setCursor(Qt.PointingHandCursor)
        foot.addWidget(self._manage_users_btn)
        rf = QPushButton("Refresh", clicked=self.refresh)
        rf.setCursor(Qt.PointingHandCursor)
        foot.addWidget(rf)
        foot.addStretch(1)
        self._footer_hint = QLabel("")
        self._footer_hint.setObjectName("muted")
        foot.addWidget(self._footer_hint)
        right_col.addLayout(foot)

        ver = QLabel(f"{APP_NAME} v{VERSION} · {get_display_shop_name()}")
        ver.setObjectName("muted")
        right_col.addWidget(ver)

        right_col.addStretch(1)
        main_row.addLayout(right_col, 3)

        root.addLayout(main_row)
        root.addStretch(1)

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _open_manage_users(self) -> None:
        if not AuthService.is_owner(getattr(self._main, "current_user", None)):
            return
        ManageUsersDialogQt(self.window(), self._main).exec()

    def _backup_now(self) -> None:
        try:
            path = self._backup.create_full_backup()
            self._footer_hint.setText("Backup completed")
            info_message(self.window(), "Backup Complete", f"Backup saved to:\n{path}")
            self._update_status_strip()
        except Exception as e:
            warning_message(self.window(), "Backup Error", str(e))

    @staticmethod
    def _short_path(path: str, max_len: int = 42) -> str:
        p = str(path)
        if len(p) <= max_len:
            return p
        return "…" + p[-(max_len - 1) :]

    @staticmethod
    def _format_delta(
        current_n: float,
        baseline_n: float,
        *,
        money: bool = False,
        vs_caption: str = "yesterday",
    ) -> str:
        diff = current_n - baseline_n
        if baseline_n == 0 and current_n == 0:
            return f"Same as {vs_caption}"
        if baseline_n == 0:
            return f"Up from zero vs {vs_caption}" if current_n > 0 else "No change"
        pct = (diff / baseline_n) * 100.0 if baseline_n else 0.0
        arrow = "↑" if diff >= 0 else "↓"
        if money:
            return f"{arrow} {format_money(abs(diff))} vs {vs_caption} ({pct:+.0f}%)"
        return f"{arrow} {abs(int(diff))} vs {vs_caption} ({pct:+.0f}%)"

    @staticmethod
    def _prior_same_length_window(start: date, end: date) -> tuple[str, str]:
        """Inclusive period immediately before ``start``..``end``, same number of days."""
        n = (end - start).days + 1
        p_end = start - timedelta(days=1)
        p_start = p_end - timedelta(days=n - 1)
        return p_start.isoformat(), p_end.isoformat()

    def _active_pill_id(self) -> int:
        if self._pill_group is None:
            return 3
        bid = self._pill_group.checkedId()
        return bid if bid >= 0 else 3

    def _overview_period_24h_combo(self) -> tuple[str, str, float, str, tuple[str, str, str]]:
        """Today / Yesterday / This week — used when the 24 h pill is selected."""
        idx = self._range_combo.currentIndex()
        t = date.today()
        if idx == 0:
            s = e = t.isoformat()
            p = t - timedelta(days=1)
            base = self._sales.aggregate_sales_range(p.isoformat(), p.isoformat())["gross_total"]
            vs = "yesterday"
            titles = ("Invoices (today)", "Cash (today)", "Sales total (today)")
        elif idx == 1:
            y = t - timedelta(days=1)
            s = e = y.isoformat()
            p = y - timedelta(days=1)
            base = self._sales.aggregate_sales_range(p.isoformat(), p.isoformat())["gross_total"]
            vs = "prior day"
            titles = ("Invoices (yesterday)", "Cash (yesterday)", "Sales total (yesterday)")
        else:
            mon = t - timedelta(days=t.weekday())
            s = mon.isoformat()
            e = t.isoformat()
            n_days = (t - mon).days + 1
            p0 = mon - timedelta(days=7)
            p1 = p0 + timedelta(days=n_days - 1)
            base = self._sales.aggregate_sales_range(p0.isoformat(), p1.isoformat())["gross_total"]
            vs = "same days last week"
            titles = (
                "Invoices (week to date)",
                "Cash (week to date)",
                "Sales total (week to date)",
            )
        return s, e, base, vs, titles

    def _overview_period_rolling(self, days: int) -> tuple[str, str, float, str, tuple[str, str, str]]:
        """Rolling window ending today; baseline = prior window of equal length."""
        t = date.today()
        start = t - timedelta(days=days - 1)
        s, e = start.isoformat(), t.isoformat()
        pb_s, pb_e = self._prior_same_length_window(start, t)
        base = self._sales.aggregate_sales_range(pb_s, pb_e)["gross_total"]
        if days == 7:
            vs, ttl = "prior 7 days", "last 7 days"
        elif days == 30:
            vs, ttl = "prior 30 days", "last 30 days"
        else:
            vs, ttl = "prior 12 months", "last 12 months"
        titles = (f"Invoices ({ttl})", f"Cash ({ttl})", f"Sales total ({ttl})")
        return s, e, base, vs, titles

    def _overview_period(self) -> tuple[str, str, float, str, tuple[str, str, str]]:
        """
        Inclusive date range for the overview hero + baseline gross for comparison +
        delta caption + (mini card titles for invoices, cash, net).

        Pills: 12 mo / 30 d / 7 d = rolling windows; 24 h uses the dropdown
        (Today, Yesterday, This week to date).
        """
        pid = self._active_pill_id()
        if pid == 0:
            return self._overview_period_rolling(365)
        if pid == 1:
            return self._overview_period_rolling(30)
        if pid == 2:
            return self._overview_period_rolling(7)
        return self._overview_period_24h_combo()

    def _sync_range_combo_for_pill(self) -> None:
        """Dropdown only applies to the 24 h pill."""
        if self._pill_group is None:
            return
        use_combo = self._active_pill_id() == 3
        self._range_combo.setEnabled(use_combo)
        self._range_combo.setToolTip(
            ""
            if use_combo
            else "Select “24 h” to choose Today, Yesterday, or This week in the list."
        )

    def _latest_backup_text(self) -> str:
        d = self._backup.backup_dir
        if not d.exists():
            return "Backups: folder missing"
        files = list(d.glob("backup_*.json"))
        if not files:
            return "Backups: none yet"
        latest = max(files, key=lambda p: p.stat().st_mtime)
        return f"Latest backup: {latest.name}"

    def _sync_manage_users_button(self) -> None:
        self._manage_users_btn.setVisible(AuthService.is_owner(getattr(self._main, "current_user", None)))

    def _update_welcome_and_info(self) -> None:
        u = getattr(self._main, "current_user", None) or {}
        shop = get_display_shop_name()
        self._welcome_label.setText(home_welcome_detail_line(u, shop))
        role = (u.get("role") or "staff").title()
        self._role_badge.setText(f"  {role}  ")

        while self._app_info_form.count():
            item = self._app_info_form.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        db_display = self._short_path(str(database_path()))
        info_rows = [
            ("App", f"{APP_NAME} v{VERSION}"),
            ("Database", db_display),
            ("User", u.get("username", "—")),
            ("Role", role),
            ("Brand primary", TOKENS.PRIMARY),
        ]
        for i, (lab, val) in enumerate(info_rows):
            self._app_info_form.addWidget(QLabel(f"{lab}:"), i, 0, Qt.AlignTop)
            self._app_info_form.addWidget(QLabel(str(val)), i, 1, Qt.AlignTop)

    def _update_status_strip(self) -> None:
        db_lbl = self._status_labels["db"]
        try:
            db.fetchone("SELECT 1")
            db_lbl.setText("● Database online")
            db_lbl.setObjectName("statusOk")
        except Exception:
            db_lbl.setText("● Database issue")
            db_lbl.setObjectName("statusBad")
        st = db_lbl.style()
        if st is not None:
            st.unpolish(db_lbl)
            st.polish(db_lbl)

        u = getattr(self._main, "current_user", None) or {}
        self._status_labels["theme"].setText(home_welcome_status_line(u, get_display_shop_name()))
        self._status_labels["backup"].setText(self._latest_backup_text())

    def _sync_appearance_switch(self) -> None:
        dark = AppSettings().get_appearance() == "dark"
        self._suppress_appearance_cb = True
        try:
            self._appearance_check.setChecked(dark)
        finally:
            self._suppress_appearance_cb = False

    def _on_appearance_toggle(self, checked: bool) -> None:
        if self._suppress_appearance_cb:
            return
        mode = "dark" if checked else "light"
        if hasattr(self._main, "apply_appearance"):
            if not self._main.apply_appearance(mode):
                warning_message(self.window(), "Theme", "Could not switch appearance.")
                self._sync_appearance_switch()
        else:
            self._sync_appearance_switch()

    def _rebuild_recent_list(self, sales_rows: list) -> None:
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        rows = sales_rows[:5]
        if not rows:
            self._recent_layout.addWidget(
                QLabel("No checkouts yet — open the register to record a sale."),
                alignment=Qt.AlignTop,
            )
            return
        for sale in rows:
            try:
                sid = int(sale.get("id"))
            except (TypeError, ValueError):
                continue
            row_w = QWidget()
            row_w.setObjectName("recentRow")
            h = QHBoxLayout(row_w)
            h.setContentsMargins(0, 8, 0, 8)
            inv = sale.get("invoice_number") or f"Order #{sale.get('id')}"
            total = float(sale.get("total_amount") or 0)
            pay = (sale.get("payment_method") or "—").upper()
            inv_l = QLabel(inv)
            inv_l.setObjectName("section")
            h.addWidget(inv_l)
            tot_l = QLabel(format_money(total))
            h.addWidget(tot_l)
            h.addStretch(1)
            pay_l = QLabel(pay)
            pay_l.setObjectName("muted")
            h.addWidget(pay_l)
            for w in (row_w, inv_l, tot_l, pay_l):
                w.setProperty("recentSaleId", sid)
                w.installEventFilter(self)
                w.setCursor(Qt.CursorShape.PointingHandCursor)
            self._recent_layout.addWidget(row_w)

    def eventFilter(self, obj, event):  # noqa: ANN001
        if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                sid = obj.property("recentSaleId")
                if sid is not None:
                    try:
                        sid_i = int(sid)
                    except (TypeError, ValueError):
                        return super().eventFilter(obj, event)
                    self._preview_recent_checkout(sid_i)
                    return True
        return super().eventFilter(obj, event)

    def _preview_recent_checkout(self, sale_id: int) -> None:
        full = self._sales.get_sale(int(sale_id))
        if not full:
            warning_message(self.window(), "Receipt", "That sale could not be loaded.")
            return
        ReceiptPreviewDialogQt(self.window(), full).exec()

    def _open_period_sales_summary(self) -> None:
        start_d, end_d, *_rest = self._overview_period()
        m = self._sales.aggregate_sales_metrics_range(start_d, end_d)
        cash = self._sales.cash_total_for_range(start_d, end_d)
        body = format_period_sales_summary(
            start_date=start_d,
            end_date=end_d,
            invoice_count=m["invoice_count"],
            subtotal_sum=m["subtotal_sum"],
            discount_sum=m["discount_sum"],
            gross_total=m["gross_total"],
            cash_total=cash,
        )
        PeriodSalesSummaryDialogQt(self.window(), start_d, end_d, body).exec()

    def refresh(self) -> None:
        self._update_welcome_and_info()
        self._sync_manage_users_button()
        self._update_status_strip()
        self._sync_appearance_switch()
        self._sync_range_combo_for_pill()

        try:
            start_d, end_d, base_gross, vs_caption, (t_inv, t_cash, t_net) = self._overview_period()
            totals = self._sales.aggregate_sales_range(start_d, end_d)
            gross = totals["gross_total"]
            invoice_count = totals["invoice_count"]
            cash = self._sales.cash_total_for_range(start_d, end_d)

            self._mini_inv_title.setText(t_inv)
            self._mini_cash_title.setText(t_cash)
            self._mini_net_title.setText(t_net)

            if self._overview_value is not None:
                self._overview_value.setText(format_money(gross))
            if self._overview_delta is not None:
                self._overview_delta.setText(
                    self._format_delta(gross, base_gross, money=True, vs_caption=vs_caption),
                )

            if self._mini_invoices is not None:
                self._mini_invoices.setText(str(invoice_count))
            if self._mini_cash is not None:
                self._mini_cash.setText(format_money(cash))
            if self._mini_net is not None:
                self._mini_net.setText(format_money(gross))

            series, chart_cap = self._sales.chart_series_for_overview(start_d, end_d)
            self._sales_chart.set_data(series, chart_cap)

            active_skus = self._inventory.get_active_product_count()
            if self._mini_skus is not None:
                self._mini_skus.setText(str(active_skus))

            low_n = self._inventory.get_low_stock_count(10)
            if self._low_card is not None:
                self._low_card.setObjectName("cardWarning" if low_n else "card")
                st = self._low_card.style()
                if st is not None:
                    st.unpolish(self._low_card)
                    st.polish(self._low_card)

            recent = self._sales.get_recent_sales(5)
            self._rebuild_recent_list(recent)

            self._footer_hint.setText(f"Updated {datetime.now().strftime('%H:%M')}")
        except Exception as e:
            if self._overview_value is not None:
                self._overview_value.setText("—")
            if self._overview_delta is not None:
                self._overview_delta.setText("")
            for lab in (self._mini_invoices, self._mini_cash, self._mini_net, self._mini_skus):
                if lab is not None:
                    lab.setText("—")
            if getattr(self, "_sales_chart", None) is not None:
                self._sales_chart.set_data([], "")
            self._footer_hint.setText(f"Could not load stats: {str(e)[:48]}")
