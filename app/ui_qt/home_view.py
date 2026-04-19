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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import PAD_LG, PAD_MD
from app.services.shop_settings import get_display_shop_name
from app.database.connection import db
from app.services.app_settings import AppSettings
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService
from app.services.receipt_output import format_period_sales_summary
from app.services.sales_service import SalesService
from app.ui.date_display import format_iso_date_as_display
from app.ui.helpers import home_welcome_detail_line, home_welcome_status_line
from app.ui_qt.dashboard_sales_chart import DashboardSalesChart
from app.ui_qt.card_components import CardFrame
from app.ui_qt.icon_utils import set_button_icon
from app.ui_qt.helpers_qt import format_money, info_message, warning_message
from app.ui_qt.dialogs_qt import PeriodSalesSummaryDialogQt, ReceiptPreviewDialogQt
from app.ui_qt.manage_users_qt import ManageUsersDialogQt


class HomeView(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._sales = SalesService()
        self._inventory = InventoryService()
        self._products = ProductService()
        self._backup = BackupService()

        self._overview_value: QLabel | None = None
        self._overview_delta: QLabel | None = None
        self._kpi_today_sales: QLabel | None = None
        self._kpi_revenue: QLabel | None = None
        self._kpi_total_products: QLabel | None = None
        self._kpi_low_stock: QLabel | None = None
        self._kpi_low_stock_card: QFrame | None = None
        self._status_labels: dict[str, QLabel] = {}
        self._recent_inner: QWidget | None = None
        self._suppress_appearance_cb = False
        self._pill_group: QButtonGroup | None = None

        inner = QWidget()
        inner.setObjectName("dashboardInner")
        inner.setMinimumWidth(0)
        inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        root = QVBoxLayout(inner)
        root.setSpacing(PAD_MD)
        root.setContentsMargins(0, 0, 0, 0)

        # Status strip
        strip = QFrame()
        strip.setObjectName("card")
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(16, 12, 16, 12)
        self._status_labels["db"] = QLabel("")
        self._status_labels["theme"] = QLabel("")
        self._status_labels["backup"] = QLabel("")
        # Long one-line QLabel text inflates minimum width and clips the right column — wrap + share space.
        for lbl in self._status_labels.values():
            lbl.setWordWrap(True)
            lbl.setMinimumWidth(0)
            lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._status_labels["db"].setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self._status_labels["theme"].setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._status_labels["backup"].setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sl.addWidget(self._status_labels["db"], 0)
        sl.addSpacing(PAD_LG)
        sl.addWidget(self._status_labels["theme"], 1)
        sl.addSpacing(PAD_LG)
        sl.addWidget(self._status_labels["backup"], 1)
        root.addWidget(strip)

        main_row = QHBoxLayout()
        main_row.setSpacing(16)
        main_row.setContentsMargins(0, 0, 0, 0)

        # ---- Left column: sales overview + recent ----
        left_panel = QWidget()
        left_panel.setMinimumWidth(0)
        left_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_col = QVBoxLayout(left_panel)
        left_col.setSpacing(16)
        left_col.setContentsMargins(0, 0, 0, 0)

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
        self._range_combo.setMinimumWidth(0)
        self._range_combo.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
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
            pb.setMinimumWidth(0)
            pb.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
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
        sum_btn.setMinimumWidth(0)
        sum_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sum_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sum_btn.setToolTip("Open a receipt-style text summary for the selected period")
        sum_btn.clicked.connect(self._open_period_sales_summary)
        set_button_icon(sum_btn, "fa5s.receipt")
        chart_hdr.addWidget(sum_btn)
        ov.addLayout(chart_hdr)
        self._sales_chart = DashboardSalesChart()
        self._sales_chart.setMinimumHeight(220)
        self._sales_chart.setMinimumWidth(0)
        self._sales_chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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

        main_row.addWidget(left_panel, 7)

        # ---- Right column: KPI cards + actions ----
        right_panel = QWidget()
        right_panel.setMinimumWidth(0)
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        right_col = QVBoxLayout(right_panel)
        right_col.setSpacing(12)
        right_col.setContentsMargins(0, 0, 0, 0)

        def _metric_card(title_text: str) -> tuple[QFrame, QLabel]:
            f = CardFrame(self, object_name="miniKpiCard", padding=(16, 14, 16, 14), spacing=6)
            f.setMinimumWidth(0)
            fl = f.content_layout
            title_label = QLabel(title_text)
            title_label.setObjectName("miniKpiTitle")
            fl.addWidget(title_label)
            value_label = QLabel("—")
            value_label.setObjectName("miniKpiValue")
            fl.addWidget(value_label)
            return f, value_label

        cards_grid = QGridLayout()
        cards_grid.setSpacing(12)
        c1, self._kpi_today_sales = _metric_card("Today Sales")
        c2, self._kpi_revenue = _metric_card("Revenue")
        c3, self._kpi_total_products = _metric_card("Total Products")
        c4, self._kpi_low_stock = _metric_card("Low Stock")
        self._kpi_low_stock_card = c4
        cards_grid.addWidget(c1, 0, 0)
        cards_grid.addWidget(c2, 0, 1)
        cards_grid.addWidget(c3, 1, 0)
        cards_grid.addWidget(c4, 1, 1)
        cards_grid.setColumnStretch(0, 1)
        cards_grid.setColumnStretch(1, 1)
        right_col.addLayout(cards_grid)

        actions = CardFrame(self, object_name="card", padding=(16, 14, 16, 14), spacing=8)
        actions.setMinimumWidth(0)
        al = actions.content_layout
        a_head = QLabel("Next moves — stock & expiry")
        a_head.setObjectName("section")
        al.addWidget(a_head)
        a_sub = QLabel(
            "Square tiles: restock (low vs minimum) and products expiring in the next 14 days. "
            "Click a tile to open Products."
        )
        a_sub.setObjectName("muted")
        a_sub.setWordWrap(True)
        al.addWidget(a_sub)
        self._actions_scroll = QScrollArea()
        self._actions_scroll.setWidgetResizable(True)
        self._actions_scroll.setFrameShape(QFrame.NoFrame)
        self._actions_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._actions_scroll.setMaximumHeight(240)
        self._actions_scroll.setMinimumWidth(0)
        self._actions_inner = QWidget()
        self._actions_inner.setMinimumWidth(0)
        self._actions_grid = QGridLayout(self._actions_inner)
        self._actions_grid.setSpacing(10)
        self._actions_grid.setContentsMargins(0, 4, 0, 0)
        self._actions_grid.setColumnStretch(0, 1)
        self._actions_grid.setColumnStretch(1, 1)
        self._actions_scroll.setWidget(self._actions_inner)
        al.addWidget(self._actions_scroll)
        right_col.addWidget(actions)

        sess = QFrame()
        sess.setObjectName("card")
        sess.setMinimumWidth(0)
        se = QVBoxLayout(sess)
        se.setContentsMargins(16, 14, 16, 14)
        seh = QLabel("Session & preferences")
        seh.setObjectName("section")
        se.addWidget(seh)
        self._welcome_label = QLabel("")
        self._welcome_label.setObjectName("pageSubtitle")
        self._welcome_label.setWordWrap(True)
        self._welcome_label.setMinimumWidth(0)
        self._welcome_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._welcome_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        se.addWidget(self._welcome_label)
        row_dm = QHBoxLayout()
        row_dm.addWidget(QLabel("Dark mode"))
        self._appearance_check = QCheckBox()
        self._appearance_check.toggled.connect(self._on_appearance_toggle)
        row_dm.addWidget(self._appearance_check)
        row_dm.addStretch(1)
        se.addLayout(row_dm)
        settings_tip = QLabel("Receipt printer, backups, and more: open Settings in the sidebar.")
        settings_tip.setObjectName("muted")
        settings_tip.setWordWrap(True)
        se.addWidget(settings_tip)
        right_col.addWidget(sess)

        foot = QHBoxLayout()
        foot.setSpacing(10)
        bu = QPushButton("Backup now", clicked=self._backup_now)
        bu.setObjectName("primary")
        bu.setCursor(Qt.PointingHandCursor)
        set_button_icon(bu, "fa5s.database")
        foot.addWidget(bu)
        self._manage_users_btn = QPushButton("Manage users", clicked=self._open_manage_users)
        self._manage_users_btn.setCursor(Qt.PointingHandCursor)
        set_button_icon(self._manage_users_btn, "fa5s.users-cog")
        foot.addWidget(self._manage_users_btn)
        rf = QPushButton("Refresh", clicked=self.refresh)
        rf.setCursor(Qt.PointingHandCursor)
        set_button_icon(rf, "fa5s.sync")
        foot.addWidget(rf)
        foot.addStretch(1)
        self._footer_hint = QLabel("")
        self._footer_hint.setObjectName("muted")
        self._footer_hint.setWordWrap(True)
        self._footer_hint.setMinimumWidth(0)
        foot.addWidget(self._footer_hint, 1)
        right_col.addLayout(foot)

        right_col.addStretch(1)
        main_row.addWidget(right_panel, 3)

        root.addLayout(main_row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(inner)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

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
            base = self._sales.aggregate_sales_range(p.isoformat(), p.isoformat())["net_total"]
            vs = "yesterday"
            titles = ("Invoices (today)", "Cash (today)", "Sales total (today)")
        elif idx == 1:
            y = t - timedelta(days=1)
            s = e = y.isoformat()
            p = y - timedelta(days=1)
            base = self._sales.aggregate_sales_range(p.isoformat(), p.isoformat())["net_total"]
            vs = "prior day"
            titles = ("Invoices (yesterday)", "Cash (yesterday)", "Sales total (yesterday)")
        else:
            mon = t - timedelta(days=t.weekday())
            s = mon.isoformat()
            e = t.isoformat()
            n_days = (t - mon).days + 1
            p0 = mon - timedelta(days=7)
            p1 = p0 + timedelta(days=n_days - 1)
            base = self._sales.aggregate_sales_range(p0.isoformat(), p1.isoformat())["net_total"]
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
        base = self._sales.aggregate_sales_range(pb_s, pb_e)["net_total"]
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
        return self._backup.latest_backup_summary()

    def _sync_manage_users_button(self) -> None:
        self._manage_users_btn.setVisible(AuthService.is_owner(getattr(self._main, "current_user", None)))

    @staticmethod
    def _fmt_qty(q: float) -> str:
        return f"{q:g}" if q == int(q) else f"{q:.1f}"

    def _action_tile_detail(self, kind: str, product: dict) -> str:
        qty = float(product.get("quantity_in_stock") or 0)
        mn = float(product.get("minimum_stock_level") or 0)
        exp = (product.get("expiry_date") or "").strip()
        exp_d = format_iso_date_as_display(exp) if exp else ""
        if kind == "expiring":
            return f"{self._fmt_qty(qty)} left · {exp_d}" if exp_d else f"{self._fmt_qty(qty)} left"
        return f"{self._fmt_qty(qty)} left · min {self._fmt_qty(mn)}"

    def _make_action_tile(self, product: dict, kind: str) -> QFrame:
        on = {"expiring": "dashboardActionTileExpiring", "low": "dashboardActionTileLow"}
        badge = {"expiring": "Expiring", "low": "Restock"}
        f = QFrame()
        f.setObjectName(on[kind])
        f.setFixedHeight(108)
        f.setMinimumWidth(0)
        f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        f.setCursor(Qt.CursorShape.PointingHandCursor)
        f.setProperty("dashboardProductId", int(product["id"]))
        f.installEventFilter(self)
        vl = QVBoxLayout(f)
        vl.setContentsMargins(8, 8, 8, 8)
        vl.setSpacing(2)
        b = QLabel(badge[kind])
        b.setObjectName("dashboardActionBadge")
        raw_name = (product.get("name") or product.get("code") or "?").strip()
        nm = QLabel(raw_name[:44] + ("…" if len(raw_name) > 44 else ""))
        nm.setWordWrap(True)
        nm.setObjectName("dashboardActionName")
        detail = QLabel(self._action_tile_detail(kind, product))
        detail.setObjectName("muted")
        detail.setWordWrap(True)
        vl.addWidget(b)
        vl.addWidget(nm, 1)
        vl.addWidget(detail)
        return f

    def _rebuild_action_grid(self) -> None:
        while self._actions_grid.count():
            item = self._actions_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        expiring = self._products.get_expiring_soon_products(14, 8)
        low = self._products.get_low_stock()[:12]
        seen: set[int] = set()
        tiles: list[tuple[dict, str]] = []
        for p in expiring:
            pid = int(p["id"])
            if pid in seen:
                continue
            seen.add(pid)
            tiles.append((p, "expiring"))
        for p in low:
            pid = int(p["id"])
            if pid in seen:
                continue
            seen.add(pid)
            tiles.append((p, "low"))

        tiles = tiles[:12]
        if not tiles:
            empty = QLabel("No restock or expiry alerts — you're in good shape.")
            empty.setObjectName("muted")
            empty.setWordWrap(True)
            self._actions_grid.addWidget(empty, 0, 0, 1, 2)
            return

        # Two columns so tiles fit the narrow right panel (3×108px overflowed).
        cols = 2
        for i, (p, kind) in enumerate(tiles):
            self._actions_grid.addWidget(self._make_action_tile(p, kind), i // cols, i % cols)

    def _open_products_for_action(self, _product_id: int) -> None:
        mw = self._main
        if hasattr(mw, "show_screen"):
            mw.show_screen("products")

    def _update_welcome_and_info(self) -> None:
        u = getattr(self._main, "current_user", None) or {}
        shop = get_display_shop_name()
        self._welcome_label.setText(home_welcome_detail_line(u, shop))

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
                dp = obj.property("dashboardProductId")
                if dp is not None:
                    try:
                        dpi = int(dp)
                    except (TypeError, ValueError):
                        return super().eventFilter(obj, event)
                    self._open_products_for_action(dpi)
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
            sales_total=m["sales_total"],
            refund_total=m["refund_total"],
            net_total=m["net_total"],
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
            start_d, end_d, base_gross, vs_caption, _titles = self._overview_period()
            totals = self._sales.aggregate_sales_range(start_d, end_d)
            gross = totals["net_total"]
            today_totals = self._sales.get_todays_totals()

            if self._overview_value is not None:
                self._overview_value.setText(format_money(gross))
            if self._overview_delta is not None:
                self._overview_delta.setText(
                    self._format_delta(gross, base_gross, money=True, vs_caption=vs_caption),
                )

            if self._kpi_today_sales is not None:
                self._kpi_today_sales.setText(str(today_totals.get("invoice_count", 0)))
            if self._kpi_revenue is not None:
                self._kpi_revenue.setText(format_money(float(today_totals.get("net_total", 0))))

            series, chart_cap = self._sales.chart_series_for_overview(start_d, end_d)
            self._sales_chart.set_data(series, chart_cap)

            active_skus = self._inventory.get_active_product_count()
            if self._kpi_total_products is not None:
                self._kpi_total_products.setText(str(active_skus))

            low_n = self._inventory.get_low_stock_count(10)
            if self._kpi_low_stock is not None:
                self._kpi_low_stock.setText(str(low_n))
            if self._kpi_low_stock_card is not None:
                self._kpi_low_stock_card.setObjectName("cardWarning" if low_n else "miniKpiCard")
                st = self._kpi_low_stock_card.style()
                if st is not None:
                    st.unpolish(self._kpi_low_stock_card)
                    st.polish(self._kpi_low_stock_card)

            recent = self._sales.get_recent_sales(5)
            self._rebuild_recent_list(recent)
            self._rebuild_action_grid()

            self._footer_hint.setText(f"Updated {datetime.now().strftime('%H:%M')}")
        except Exception as e:
            if self._overview_value is not None:
                self._overview_value.setText("—")
            if self._overview_delta is not None:
                self._overview_delta.setText("")
            for lab in (self._kpi_today_sales, self._kpi_revenue, self._kpi_total_products, self._kpi_low_stock):
                if lab is not None:
                    lab.setText("—")
            if getattr(self, "_sales_chart", None) is not None:
                self._sales_chart.set_data([], "")
            try:
                self._rebuild_action_grid()
            except Exception:
                pass
            self._footer_hint.setText(f"Could not load stats: {str(e)[:48]}")
