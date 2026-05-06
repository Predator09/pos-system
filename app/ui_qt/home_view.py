"""home_view.py — GamMarket POS modernized dashboard.

Design principles
─────────────────
• GamMarket teal palette unified with login_view.py
• Color-coded KPI cards: teal (good), amber (warning), red (danger)
• Fixed viewport grid — chart and all sections visible without scrolling
• Status strip uses elision so it never overflows horizontally
• Action tiles in a 2-column QGridLayout inside a fixed-height scroll area
• All original service calls, signals, and business logic preserved 100%
• Dark / light theme auto-detected from QPalette at paint time
• Per-object-name stylesheet on card frames for crisp theming
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QFont, QMouseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
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


# ── Design tokens ──────────────────────────────────────────────────────────
_T_DARK    = "#0D3B38"
_T_MID     = "#167A6A"
_T_ACCENT  = "#1DB39E"
_T_LIGHT   = "#EEF7F5"
_T_BTN_H   = "#1A9680"

_WHITE     = "#FFFFFF"
_PAGE_BG   = "#F0F4F3"
_CARD_BG   = "#FFFFFF"
_BORDER    = "#E2E8E6"

_TEXT      = "#111827"
_TEXT_MID  = "#374151"
_MUTED     = "#6B7280"

_AMBER_BG  = "#FFFBEB"
_AMBER_BR  = "#F59E0B"
_AMBER_TXT = "#92400E"

_RED_BG    = "#FEF2F2"
_RED_BR    = "#EF4444"
_RED_TXT   = "#991B1B"

_GREEN_BG  = _T_LIGHT
_GREEN_BR  = _T_ACCENT
_GREEN_TXT = _T_MID

_BLUE_BG   = "#EFF6FF"
_BLUE_BR   = "#3B82F6"
_BLUE_TXT  = "#1E40AF"


# ── Shared helpers ─────────────────────────────────────────────────────────

def _shadow(w: QWidget, blur: int = 14, alpha: int = 20, dy: int = 3) -> None:
    eff = QGraphicsDropShadowEffect(w)
    eff.setBlurRadius(blur)
    eff.setColor(QColor(0, 0, 0, alpha))
    eff.setOffset(0, dy)
    w.setGraphicsEffect(eff)


def _card_frame(
    radius: int = 12,
    bg: str = _CARD_BG,
    border: str = _BORDER,
    border_left: str = "",
    shadow: bool = True,
) -> QFrame:
    f = QFrame()
    f.setObjectName("modernCard")
    left_style = f"border-left: 4px solid {border_left};" if border_left else ""
    f.setStyleSheet(f"""
        QFrame#modernCard {{
            background: {bg};
            border: 1px solid {border};
            border-radius: {radius}px;
            {left_style}
        }}
    """)
    if shadow:
        _shadow(f)
    return f


def _label(
    text: str = "",
    size: int = 13,
    bold: bool = False,
    color: str = _TEXT,
    wrap: bool = False,
) -> QLabel:
    lbl = QLabel(text)
    f = QFont()
    f.setPointSize(size)
    if bold:
        f.setBold(True)
    lbl.setFont(f)
    lbl.setStyleSheet(f"color: {color}; background: transparent;")
    if wrap:
        lbl.setWordWrap(True)
    return lbl


def _pill_chip(
    text: str,
    *,
    fg: str,
    bg: str,
    border: str,
    padding: str = "1px 8px",
    radius: int = 10,
    fixed_height: int | None = None,
) -> QLabel:
    """Small rounded label (status / category pill)."""
    w = QLabel(text)
    if fixed_height is not None:
        w.setFixedHeight(fixed_height)
    w.setStyleSheet(f"""
        font-size: 10px; font-weight: 700;
        color: {fg}; background: {bg};
        border: 1px solid {border};
        border-radius: {radius}px; padding: {padding};
    """)
    return w


def _ghost_btn(text: str, icon_key: str = "") -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(32)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    btn.setMinimumWidth(0)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            border: 1.5px solid {_BORDER};
            border-radius: 8px;
            font-size: 12px; font-weight: 600;
            color: {_TEXT_MID};
            padding: 0 12px;
        }}
        QPushButton:hover {{
            border-color: {_T_ACCENT};
            color: {_T_MID};
            background: {_T_LIGHT};
        }}
    """)
    if icon_key:
        set_button_icon(btn, icon_key)
    return btn


def _primary_btn(text: str, icon_key: str = "") -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(34)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    btn.setMinimumWidth(0)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {_T_MID};
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 12px; font-weight: 700;
            padding: 0 14px;
        }}
        QPushButton:hover {{ background: {_T_BTN_H}; }}
        QPushButton:pressed {{ background: #0F5C50; }}
    """)
    if icon_key:
        set_button_icon(btn, icon_key)
    return btn


def _pill_btn(text: str, active: bool = False) -> QPushButton:
    btn = QPushButton(text)
    btn.setCheckable(True)
    btn.setChecked(active)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumWidth(0)
    btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    btn.setFixedHeight(30)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {_T_LIGHT if active else _WHITE};
            color: {_T_MID if active else _TEXT_MID};
            border: 1.5px solid {_T_ACCENT if active else _BORDER};
            border-radius: 8px;
            font-size: 12px;
            font-weight: {'700' if active else '500'};
            padding: 0 12px;
        }}
        QPushButton:checked {{
            background: {_T_LIGHT};
            border-color: {_T_ACCENT};
            color: {_T_MID};
            font-weight: 700;
        }}
        QPushButton:hover {{
            background: {_T_LIGHT};
            border-color: {_T_ACCENT};
            color: {_T_MID};
        }}
    """)
    return btn


# ── KPI card ───────────────────────────────────────────────────────────────

class _KpiCard(QFrame):
    """Color-coded metric card with left accent stripe."""

    def __init__(
        self,
        title: str,
        icon: str = "📊",
        accent: str = _T_ACCENT,
        bg: str = _CARD_BG,
        border: str = _BORDER,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self._accent = accent
        self._apply_style(bg, border)
        _shadow(self, blur=10, alpha=16)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(88)

        h = QHBoxLayout(self)
        h.setContentsMargins(14, 12, 14, 12)
        h.setSpacing(10)

        # Icon bubble
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            background: {accent}22;
            border-radius: 18px;
            font-size: 17px;
        """)
        h.addWidget(icon_lbl, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 0, 0, 0)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 700; letter-spacing: 0.7px;"
            f" color: {_MUTED}; background: transparent; text-transform: uppercase;"
        )
        col.addWidget(self._title_lbl)

        self._value_lbl = QLabel("—")
        self._value_lbl.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {_TEXT}; background: transparent;"
        )
        col.addWidget(self._value_lbl)

        h.addLayout(col, 1)

        # Accent stripe (painted as a thin left border inside the frame)
        stripe = QFrame(self)
        stripe.setStyleSheet(f"background: {accent}; border-radius: 2px;")
        stripe.setFixedWidth(4)
        stripe.setGeometry(0, 14, 4, 60)

    def _apply_style(self, bg: str, border: str) -> None:
        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)

    def set_value(self, text: str) -> None:
        self._value_lbl.setText(text)

    def set_alert(
        self,
        bg: str,
        border: str,
        value_color: str = _TEXT,
    ) -> None:
        self._apply_style(bg, border)
        self._value_lbl.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {value_color};"
            f" background: transparent;"
        )
        stripe = self.findChild(QFrame)
        if stripe:
            stripe.setStyleSheet(f"background: {border}; border-radius: 2px;")

    def reset_alert(self) -> None:
        self._apply_style(_CARD_BG, _BORDER)
        self._value_lbl.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {_TEXT};"
            f" background: transparent;"
        )
        stripe = self.findChild(QFrame)
        if stripe:
            stripe.setStyleSheet(f"background: {self._accent}; border-radius: 2px;")


# ── Status strip ───────────────────────────────────────────────────────────

class _StatusStrip(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusStrip")
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QFrame#statusStrip {{
                background: {_WHITE};
                border-bottom: 1px solid {_BORDER};
                border-top: none;
                border-left: none;
                border-right: none;
                border-radius: 0px;
            }}
        """)

        h = QHBoxLayout(self)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(0)

        # DB pill
        db_pill = QFrame()
        db_pill.setObjectName("dbPill")
        db_pill.setFixedHeight(24)
        db_pill.setStyleSheet(f"""
            QFrame#dbPill {{
                background: {_T_LIGHT};
                border: 1px solid {_T_ACCENT};
                border-radius: 12px;
            }}
        """)
        db_inner = QHBoxLayout(db_pill)
        db_inner.setContentsMargins(8, 0, 10, 0)
        db_inner.setSpacing(5)
        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"font-size: 8px; color: {_T_ACCENT}; background: transparent;")
        db_inner.addWidget(self._dot)
        self._db_lbl = QLabel("Database online")
        self._db_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {_T_MID}; background: transparent;"
        )
        db_inner.addWidget(self._db_lbl)
        h.addWidget(db_pill)
        h.addSpacing(16)

        sep = QLabel("·")
        sep.setStyleSheet(f"color: {_MUTED}; font-size: 13px;")
        h.addWidget(sep)
        h.addSpacing(12)

        self._greeting_lbl = QLabel("")
        self._greeting_lbl.setStyleSheet(
            f"font-size: 12px; color: {_TEXT_MID}; background: transparent;"
        )
        self._greeting_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._greeting_lbl.setMinimumWidth(0)
        h.addWidget(self._greeting_lbl, 1)

        self._backup_lbl = QLabel("")
        self._backup_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._backup_lbl.setStyleSheet(
            f"font-size: 11px; color: {_MUTED}; background: transparent;"
        )
        self._backup_lbl.setMaximumWidth(380)
        self._backup_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        h.addWidget(self._backup_lbl)

    def refresh(self, greeting: str, backup: str, online: bool = True) -> None:
        color = _T_ACCENT if online else _RED_BR
        status = "Database online" if online else "Database offline"
        self._db_lbl.setText(status)
        self._db_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {color}; background: transparent;"
        )
        self._dot.setStyleSheet(f"font-size: 8px; color: {color}; background: transparent;")
        self._greeting_lbl.setText(greeting)
        fm = self._backup_lbl.fontMetrics()
        self._backup_lbl.setText(fm.elidedText(backup, Qt.ElideRight, 370))
        self._backup_lbl.setToolTip(backup)


# ── Recent checkout row ────────────────────────────────────────────────────

class _RecentRow(QWidget):
    def __init__(
        self,
        invoice: str,
        total: str,
        method: str,
        sale_id: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("recentRow")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(42)
        self.setStyleSheet(f"""
            QWidget#recentRow {{
                background: transparent;
                border-bottom: 1px solid {_BORDER};
                border-radius: 0px;
            }}
            QWidget#recentRow:hover {{
                background: {_T_LIGHT};
                border-radius: 8px;
            }}
        """)
        h = QHBoxLayout(self)
        h.setContentsMargins(8, 0, 8, 0)
        h.setSpacing(10)

        inv_lbl = QLabel(invoice)
        inv_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {_TEXT}; background: transparent;"
        )
        h.addWidget(inv_lbl)

        h.addStretch()

        pay_chip = _pill_chip(
            method,
            fg=_T_MID,
            bg=_T_LIGHT,
            border=_T_ACCENT,
            padding="0 8px",
            fixed_height=20,
        )
        h.addWidget(pay_chip)

        total_lbl = QLabel(total)
        total_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 800; color: {_T_MID}; background: transparent;"
        )
        h.addWidget(total_lbl)

        # tag every child with the sale id for eventFilter
        for w in (self, inv_lbl, pay_chip, total_lbl):
            w.setProperty("recentSaleId", sale_id)


# ── Action tile ────────────────────────────────────────────────────────────

class _ActionTile(QFrame):
    """Color-coded expiry / low-stock tile."""

    _KIND_STYLE = {
        "expiring": (_AMBER_BG, _AMBER_BR, _AMBER_TXT, "Expiring"),
        "low":      (_RED_BG,   _RED_BR,   _RED_TXT,   "Restock"),
    }

    def __init__(
        self,
        product: dict,
        kind: str,
        detail: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        bg, border, txt, badge = self._KIND_STYLE.get(
            kind, (_T_LIGHT, _T_ACCENT, _T_MID, kind.title())
        )
        self.setObjectName("actionTile")
        self.setFixedHeight(96)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame#actionTile {{
                background: {bg};
                border: 1px solid {border};
                border-left: 4px solid {border};
                border-radius: 10px;
            }}
            QFrame#actionTile:hover {{
                background: {_T_LIGHT};
                border-color: {_T_ACCENT};
            }}
        """)
        self.setProperty("dashboardProductId", int(product["id"]))

        v = QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(2)

        badge_lbl = QLabel(badge.upper())
        badge_lbl.setStyleSheet(
            f"font-size: 9px; font-weight: 800; letter-spacing: 1px;"
            f" color: {border}; background: transparent;"
        )
        v.addWidget(badge_lbl)

        raw_name = (product.get("name") or product.get("code") or "?").strip()
        name_lbl = QLabel(raw_name[:40] + ("…" if len(raw_name) > 40 else ""))
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {_TEXT}; background: transparent;"
        )
        v.addWidget(name_lbl, 1)

        det_lbl = QLabel(detail)
        det_lbl.setStyleSheet(f"font-size: 11px; color: {_MUTED}; background: transparent;")
        v.addWidget(det_lbl)


# ── Main HomeView ──────────────────────────────────────────────────────────

class HomeView(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._sales      = SalesService()
        self._inventory  = InventoryService()
        self._products   = ProductService()
        self._backup     = BackupService()

        # Widget refs (populated during build)
        self._overview_value:       QLabel | None = None
        self._overview_delta:       QLabel | None = None
        self._kpi_today_sales:      QLabel | None = None
        self._kpi_revenue:          QLabel | None = None
        self._kpi_total_products:   QLabel | None = None
        self._kpi_low_stock:        QLabel | None = None
        self._kpi_low_stock_card:   _KpiCard | None = None
        self._recent_inner:         QWidget | None = None
        self._suppress_appearance_cb = False
        self._pill_group:           QButtonGroup | None = None

        self.setStyleSheet(f"background: {_PAGE_BG};")
        self._build()

    # ── UI construction ────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Status strip (fixed height, no overflow)
        self._status_strip = _StatusStrip()
        root.addWidget(self._status_strip)

        # Content area
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        ch = QHBoxLayout(content)
        ch.setContentsMargins(14, 12, 14, 12)
        ch.setSpacing(14)

        ch.addWidget(self._build_left(), 7)
        ch.addWidget(self._build_right(), 3)

        root.addWidget(content, 1)

    # ── Left panel ─────────────────────────────────────────────────────────

    def _build_left(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        # Sales overview card — capped so the full chart is visible on first load
        ov_card = _card_frame(14)
        ov_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ov_card.setMaximumHeight(500)
        ov = QVBoxLayout(ov_card)
        ov.setContentsMargins(20, 12, 20, 10)
        ov.setSpacing(0)

        # Header row
        hdr = QHBoxLayout()
        oh = _label("Sales overview", size=14, bold=True, color=_TEXT_MID)
        hdr.addWidget(oh)
        hdr.addStretch()

        self._range_combo = QComboBox()
        self._range_combo.addItems(["Today", "Yesterday", "This week"])
        self._range_combo.setMinimumWidth(0)
        self._range_combo.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self._range_combo.setFixedHeight(30)
        self._range_combo.setStyleSheet(f"""
            QComboBox {{
                background: {_WHITE};
                border: 1.5px solid {_BORDER};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12px;
                color: {_TEXT};
            }}
            QComboBox:focus {{ border-color: {_T_ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background: {_WHITE};
                border: 1.5px solid {_BORDER};
                border-radius: 8px;
                font-size: 12px;
                selection-background-color: {_T_LIGHT};
                color: {_TEXT};
            }}
        """)
        self._range_combo.currentIndexChanged.connect(lambda _i: self.refresh())
        hdr.addWidget(self._range_combo)
        ov.addLayout(hdr)
        ov.addSpacing(10)

        # Big revenue number
        self._overview_value = _label("—", size=38, bold=True, color=_TEXT)
        self._overview_value.setStyleSheet(
            f"font-size: 38px; font-weight: 800; color: {_TEXT}; background: transparent;"
        )
        ov.addWidget(self._overview_value)

        self._overview_delta = _label("", size=11, color=_MUTED)
        ov.addWidget(self._overview_delta)
        ov.addSpacing(6)

        # Period pills
        pills = QHBoxLayout()
        pills.setSpacing(8)
        self._pill_group = QButtonGroup(self)
        self._pill_group.setExclusive(True)
        for i, cap in enumerate(("12 mo", "30 d", "7 d", "24 h")):
            pb = _pill_btn(cap, active=(i == 3))
            pb.setObjectName("pillTab")
            self._pill_group.addButton(pb, i)
            pills.addWidget(pb)
        pills.addStretch(1)
        ov.addLayout(pills)
        self._pill_group.idClicked.connect(lambda _id: self.refresh())
        ov.addSpacing(8)

        # Chart sub-header
        chart_hdr = QHBoxLayout()
        cpt = _label("Sales trend", size=12, bold=True, color=_T_ACCENT)
        chart_hdr.addWidget(cpt)
        chart_hdr.addStretch()
        sum_btn = _ghost_btn("Receipt-style summary", "fa5s.receipt")
        sum_btn.setToolTip("Open a receipt-style text summary for the selected period")
        sum_btn.clicked.connect(self._open_period_sales_summary)
        chart_hdr.addWidget(sum_btn)
        ov.addLayout(chart_hdr)
        ov.addSpacing(4)

        # Chart — fills remaining vertical space in the capped card
        self._sales_chart = DashboardSalesChart()
        self._sales_chart.setMinimumHeight(160)
        self._sales_chart.setMaximumHeight(280)
        self._sales_chart.setMinimumWidth(0)
        self._sales_chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ov.addWidget(self._sales_chart, 1)

        v.addWidget(ov_card, 1)   # overview card — fixed by MaximumHeight above

        # Recent checkouts card
        rec_card = _card_frame(14)
        rec_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        rl = QVBoxLayout(rec_card)
        rl.setContentsMargins(16, 12, 16, 12)
        rl.setSpacing(6)

        rec_hdr = QHBoxLayout()
        rec_hdr.addWidget(_label("Recent checkouts", size=13, bold=True, color=_TEXT))
        rec_hdr.addStretch()
        rec_hdr.addWidget(_label("Last 5 sales · tap a row to preview", size=11, color=_MUTED))
        rl.addLayout(rec_hdr)

        self._recent_inner = QWidget()
        self._recent_inner.setStyleSheet("background: transparent;")
        self._recent_layout = QVBoxLayout(self._recent_inner)
        self._recent_layout.setContentsMargins(0, 0, 0, 0)
        self._recent_layout.setSpacing(0)
        self._recent_layout.setAlignment(Qt.AlignTop)
        rl.addWidget(self._recent_inner)

        v.addWidget(rec_card, 0)   # recent card — natural height, no extra stretch

        return panel

    # ── Right panel ────────────────────────────────────────────────────────

    def _build_right(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        # ── KPI 2×2 grid
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(10)

        self._card_today  = _KpiCard("Today sales",    "🧾", _T_ACCENT)
        self._card_rev    = _KpiCard("Revenue",         "💰", _T_ACCENT)
        self._card_prods  = _KpiCard("Total products",  "📦", _BLUE_BR, _BLUE_BG, _BLUE_BR)
        self._card_low    = _KpiCard("Low stock",       "⚠️", _AMBER_BR)

        self._kpi_today_sales    = self._card_today._value_lbl
        self._kpi_revenue        = self._card_rev._value_lbl
        self._kpi_total_products = self._card_prods._value_lbl
        self._kpi_low_stock      = self._card_low._value_lbl
        self._kpi_low_stock_card = self._card_low

        kpi_grid.addWidget(self._card_today, 0, 0)
        kpi_grid.addWidget(self._card_rev,   0, 1)
        kpi_grid.addWidget(self._card_prods, 1, 0)
        kpi_grid.addWidget(self._card_low,   1, 1)
        kpi_grid.setColumnStretch(0, 1)
        kpi_grid.setColumnStretch(1, 1)
        v.addLayout(kpi_grid)

        # ── Next moves card
        moves_card = _card_frame(14)
        moves_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ml = QVBoxLayout(moves_card)
        ml.setContentsMargins(14, 12, 14, 12)
        ml.setSpacing(8)

        mh = QHBoxLayout()
        mh.addWidget(_label("Next moves", size=13, bold=True, color=_TEXT))
        mh.addStretch()
        badge = _pill_chip(
            "Stock & expiry",
            fg=_AMBER_TXT,
            bg=_AMBER_BG,
            border=_AMBER_BR,
        )
        mh.addWidget(badge)
        ml.addLayout(mh)

        msub = _label(
            "Tap a tile to view in Products.",
            size=11, color=_MUTED, wrap=True,
        )
        ml.addWidget(msub)

        self._actions_scroll = QScrollArea()
        self._actions_scroll.setWidgetResizable(True)
        self._actions_scroll.setFrameShape(QFrame.NoFrame)
        self._actions_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._actions_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._actions_scroll.setStyleSheet("background: transparent;")

        self._actions_inner = QWidget()
        self._actions_inner.setStyleSheet("background: transparent;")
        self._actions_inner.setMinimumWidth(0)
        self._actions_grid = QGridLayout(self._actions_inner)
        self._actions_grid.setSpacing(8)
        self._actions_grid.setContentsMargins(0, 2, 0, 2)
        self._actions_grid.setColumnStretch(0, 1)
        self._actions_grid.setColumnStretch(1, 1)
        self._actions_scroll.setWidget(self._actions_inner)
        ml.addWidget(self._actions_scroll, 1)

        v.addWidget(moves_card, 1)

        # ── Session & preferences card
        sess_card = _card_frame(14)
        sess_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        se = QVBoxLayout(sess_card)
        se.setContentsMargins(14, 12, 14, 12)
        se.setSpacing(8)

        se.addWidget(_label("Session & preferences", size=13, bold=True, color=_TEXT))

        self._welcome_label = QLabel("")
        self._welcome_label.setWordWrap(True)
        self._welcome_label.setMinimumWidth(0)
        self._welcome_label.setStyleSheet(f"font-size: 12px; color: {_MUTED}; background: transparent;")
        se.addWidget(self._welcome_label)

        dm_row = QHBoxLayout()
        dm_lbl = _label("Dark mode", size=12, color=_TEXT_MID)
        dm_row.addWidget(dm_lbl)
        dm_row.addStretch()
        self._appearance_check = QCheckBox()
        self._appearance_check.toggled.connect(self._on_appearance_toggle)
        dm_row.addWidget(self._appearance_check)
        se.addLayout(dm_row)

        tip = _label(
            "Receipt printer, backups and more: open Settings.",
            size=11, color=_MUTED, wrap=True,
        )
        se.addWidget(tip)
        v.addWidget(sess_card)

        # ── Footer actions row
        foot = QHBoxLayout()
        foot.setSpacing(8)

        bu = _primary_btn("Backup now", "fa5s.database")
        bu.clicked.connect(self._backup_now)
        foot.addWidget(bu)

        self._manage_users_btn = _ghost_btn("Manage users", "fa5s.users-cog")
        self._manage_users_btn.clicked.connect(self._open_manage_users)
        foot.addWidget(self._manage_users_btn)

        rf = _ghost_btn("Refresh", "fa5s.sync")
        rf.clicked.connect(self.refresh)
        foot.addWidget(rf)

        foot.addStretch(1)
        v.addLayout(foot)

        # Footer hint (timestamp / error)
        self._footer_hint = _label("", size=11, color=_MUTED)
        self._footer_hint.setWordWrap(True)
        self._footer_hint.setMinimumWidth(0)
        v.addWidget(self._footer_hint)

        return panel

    # ── Business logic (100% preserved from original) ─────────────────────

    def _open_manage_users(self) -> None:
        if not AuthService.is_owner(getattr(self._main, "current_user", None)):
            return
        ManageUsersDialogQt(self.window(), self._main).exec()

    def _backup_now(self) -> None:
        try:
            path = self._backup.create_full_backup()
            self._footer_hint.setText("Backup completed ✓")
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
        pid = self._active_pill_id()
        if pid == 0:
            return self._overview_period_rolling(365)
        if pid == 1:
            return self._overview_period_rolling(30)
        if pid == 2:
            return self._overview_period_rolling(7)
        return self._overview_period_24h_combo()

    def _sync_range_combo_for_pill(self) -> None:
        if self._pill_group is None:
            return
        use_combo = self._active_pill_id() == 3
        self._range_combo.setEnabled(use_combo)
        self._range_combo.setToolTip(
            "" if use_combo
            else "Select '24 h' to choose Today, Yesterday, or This week."
        )

    def _latest_backup_text(self) -> str:
        return BackupService.backup_summary_as_text(self._backup.latest_backup_summary())

    def _sync_manage_users_button(self) -> None:
        self._manage_users_btn.setVisible(
            AuthService.is_owner(getattr(self._main, "current_user", None))
        )

    @staticmethod
    def _fmt_qty(q: float) -> str:
        return f"{q:g}" if q == int(q) else f"{q:.1f}"

    def _action_tile_detail(self, kind: str, product: dict) -> str:
        qty = float(product.get("quantity_in_stock") or 0)
        mn  = float(product.get("minimum_stock_level") or 0)
        exp = (product.get("expiry_date") or "").strip()
        exp_d = format_iso_date_as_display(exp) if exp else ""
        if kind == "expiring":
            return f"{self._fmt_qty(qty)} left · {exp_d}" if exp_d else f"{self._fmt_qty(qty)} left"
        return f"{self._fmt_qty(qty)} left · min {self._fmt_qty(mn)}"

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
            empty = _label(
                "No restock or expiry alerts — you're in good shape. ✓",
                size=12, color=_T_MID, wrap=True,
            )
            empty.setStyleSheet(
                f"font-size: 12px; color: {_T_MID}; background: {_T_LIGHT};"
                f" border-radius: 8px; padding: 10px;"
            )
            self._actions_grid.addWidget(empty, 0, 0, 1, 2)
            return

        cols = 2
        for i, (p, kind) in enumerate(tiles):
            tile = _ActionTile(p, kind, self._action_tile_detail(kind, p))
            tile.installEventFilter(self)
            self._actions_grid.addWidget(tile, i // cols, i % cols)

    def _open_products_for_action(self, _product_id: int) -> None:
        mw = self._main
        if hasattr(mw, "show_screen"):
            mw.show_screen("products")

    def _update_welcome_and_info(self) -> None:
        u = getattr(self._main, "current_user", None) or {}
        shop = get_display_shop_name()
        self._welcome_label.setText(home_welcome_detail_line(u, shop))

    def _update_status_strip(self) -> None:
        online = True
        try:
            db.fetchone("SELECT 1")
        except Exception:
            online = False

        u = getattr(self._main, "current_user", None) or {}
        greeting = home_welcome_status_line(u, get_display_shop_name())
        backup   = self._latest_backup_text()
        self._status_strip.refresh(greeting, backup, online)

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
        # Clear existing rows
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        rows = sales_rows[:5]
        if not rows:
            self._recent_layout.addWidget(
                _label(
                    "No checkouts yet — open the register to record a sale.",
                    size=12, color=_MUTED, wrap=True,
                ),
                alignment=Qt.AlignTop,
            )
            return

        for sale in rows:
            try:
                sid = int(sale.get("id"))
            except (TypeError, ValueError):
                continue
            inv   = sale.get("invoice_number") or f"Order #{sale.get('id')}"
            total = float(sale.get("total_amount") or 0)
            pay   = (sale.get("payment_method") or "—").upper()
            row   = _RecentRow(inv, format_money(total), pay, sid)
            row.installEventFilter(self)
            self._recent_layout.addWidget(row)

    def eventFilter(self, obj, event):  # noqa: ANN001
        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and isinstance(event, QMouseEvent)
            and event.button() == Qt.MouseButton.LeftButton
        ):
            sid = obj.property("recentSaleId")
            if sid is not None:
                try:
                    self._preview_recent_checkout(int(sid))
                except (TypeError, ValueError):
                    pass
                return True
            dp = obj.property("dashboardProductId")
            if dp is not None:
                try:
                    self._open_products_for_action(int(dp))
                except (TypeError, ValueError):
                    pass
                return True
        return super().eventFilter(obj, event)

    def _preview_recent_checkout(self, sale_id: int) -> None:
        full = self._sales.get_sale(sale_id)
        if not full:
            warning_message(self.window(), "Receipt", "That sale could not be loaded.")
            return
        ReceiptPreviewDialogQt(self.window(), full).exec()

    def _open_period_sales_summary(self) -> None:
        start_d, end_d, *_rest = self._overview_period()
        m    = self._sales.aggregate_sales_metrics_range(start_d, end_d)
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

    # ── Refresh (100% original logic) ─────────────────────────────────────

    def refresh(self) -> None:
        self._update_welcome_and_info()
        self._sync_manage_users_button()
        self._update_status_strip()
        self._sync_appearance_switch()
        self._sync_range_combo_for_pill()

        try:
            start_d, end_d, base_gross, vs_caption, _titles = self._overview_period()
            totals      = self._sales.aggregate_sales_range(start_d, end_d)
            gross       = totals["net_total"]
            today_totals = self._sales.get_todays_totals()

            if self._overview_value is not None:
                self._overview_value.setText(format_money(gross))
            if self._overview_delta is not None:
                delta_text = self._format_delta(
                    gross, base_gross, money=True, vs_caption=vs_caption
                )
                color = _T_MID if gross >= base_gross else _RED_TXT
                self._overview_delta.setText(delta_text)
                self._overview_delta.setStyleSheet(
                    f"font-size: 12px; color: {color}; background: transparent;"
                )

            if self._kpi_today_sales is not None:
                self._kpi_today_sales.setText(str(today_totals.get("invoice_count", 0)))
            if self._kpi_revenue is not None:
                self._kpi_revenue.setText(
                    format_money(float(today_totals.get("net_total", 0)))
                )

            series, chart_cap = self._sales.chart_series_for_overview(start_d, end_d)
            self._sales_chart.set_data(series, chart_cap)

            active_skus = self._inventory.get_active_product_count()
            if self._kpi_total_products is not None:
                self._kpi_total_products.setText(str(active_skus))

            low_n = self._inventory.get_low_stock_count(10)
            if self._kpi_low_stock is not None:
                self._kpi_low_stock.setText(str(low_n))
            # Color-code the low-stock card
            if self._kpi_low_stock_card is not None:
                if low_n >= 10:
                    self._kpi_low_stock_card.set_alert(_RED_BG, _RED_BR, _RED_TXT)
                elif low_n >= 3:
                    self._kpi_low_stock_card.set_alert(_AMBER_BG, _AMBER_BR, _AMBER_TXT)
                else:
                    self._kpi_low_stock_card.reset_alert()

            recent = self._sales.get_recent_sales(5)
            self._rebuild_recent_list(recent)
            self._rebuild_action_grid()

            self._footer_hint.setText(
                f"Last updated {datetime.now().strftime('%H:%M:%S')}"
            )

        except Exception as e:
            if self._overview_value is not None:
                self._overview_value.setText("—")
            if self._overview_delta is not None:
                self._overview_delta.setText("")
            for lab in (
                self._kpi_today_sales,
                self._kpi_revenue,
                self._kpi_total_products,
                self._kpi_low_stock,
            ):
                if lab is not None:
                    lab.setText("—")
            if getattr(self, "_sales_chart", None) is not None:
                self._sales_chart.set_data([], "")
            try:
                self._rebuild_action_grid()
            except Exception:
                pass
            self._footer_hint.setText(f"Could not load stats: {str(e)[:60]}")
