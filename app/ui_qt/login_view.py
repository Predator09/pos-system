"""Sign-in screen — Smartstock POS visual design.

Matches the two-panel layout from the design mockup:
  Left  — dark teal brand panel (logo, headline, feature list)
  Right — white form panel (shop picker, credentials, sign-in button)

All business logic is unchanged from the refactored ViewModel version.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator
import sqlite3

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import db
from app.services.auth_service import AuthService
from app.services.shop_context import (
    create_new_shop,
    database_path,
    get_current_shop_id,
    list_shops,
    open_shop_database,
    shop_combo_entries,
)
from app.services.shop_settings import ShopSettings, get_display_shop_name
from app.ui_qt.helpers_qt import warning_message
from app.ui_qt.icon_utils import set_button_icon
from app.ui_qt.logo_widget import ShopLogoLabel

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
_TEAL_DARK   = "#0D3B38"
_TEAL_ACCENT = "#1DB39E"
_TEAL_BTN    = "#167A6A"
_TEAL_BTN_H  = "#1A9680"
_GREY_BG     = "#F5F7F8"
_GREY_CARD   = "#FFFFFF"
_GREY_BORDER = "#E2E6EA"
_GREY_TEXT   = "#6B7280"
_GREY_LABEL  = "#374151"
_TEXT_DARK   = "#111827"
_SAFE_BG     = "#EEF7F5"
_ERROR_RED   = "#DC2626"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_password(text: str) -> str:
    return (text or "").replace("\r", "").replace("\n", "")


def _label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size: 13px; font-weight: 600; color: {_GREY_LABEL};"
        " background: transparent;"
    )
    return lbl


def _primary_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setMinimumHeight(48)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {_TEAL_BTN};
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
        }}
        QPushButton:hover  {{ background: {_TEAL_BTN_H}; }}
        QPushButton:pressed {{ background: #0F5C50; }}
    """)
    return btn


def _ghost_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setMinimumHeight(48)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {_TEAL_BTN};
            border: 1.5px solid {_TEAL_ACCENT};
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: {_SAFE_BG}; }}
    """)
    return btn


def _styled_input(placeholder: str = "", password: bool = False) -> QLineEdit:
    w = QLineEdit()
    w.setPlaceholderText(placeholder)
    w.setMinimumHeight(42)
    if password:
        w.setEchoMode(QLineEdit.EchoMode.Password)
    w.setStyleSheet(f"""
        QLineEdit {{
            background: {_GREY_BG};
            border: 1.5px solid {_GREY_BORDER};
            border-radius: 8px;
            padding: 0 12px;
            font-size: 14px;
            color: {_TEXT_DARK};
        }}
        QLineEdit:focus {{ border-color: {_TEAL_ACCENT}; }}
    """)
    return w


def _icon_frame(left_icon: str, edit: QLineEdit,
                right_widget: QWidget | None = None) -> QFrame:
    """Return a bordered frame containing [icon | lineEdit | optional-right-widget]."""
    frame = QFrame()
    frame.setFixedHeight(50)
    frame.setStyleSheet(f"""
        QFrame {{
            background: {_GREY_CARD};
            border: 1.5px solid {_GREY_BORDER};
            border-radius: 10px;
        }}
    """)
    h = QHBoxLayout(frame)
    h.setContentsMargins(0, 0, 8, 0)
    h.setSpacing(0)

    left = QLabel(left_icon)
    left.setFixedWidth(44)
    left.setAlignment(Qt.AlignCenter)
    left.setStyleSheet(f"font-size: 16px; background: transparent; color: {_GREY_TEXT};")
    h.addWidget(left)

    edit.setStyleSheet(f"""
        QLineEdit {{
            background: transparent;
            border: none;
            font-size: 14px;
            color: {_TEXT_DARK};
            padding: 0;
        }}
        QLineEdit::placeholder {{ color: {_GREY_TEXT}; }}
    """)
    edit.setMinimumHeight(46)
    h.addWidget(edit, 1)

    if right_widget:
        right_widget.setStyleSheet("background: transparent; border: none;")
        h.addWidget(right_widget)

    return frame


# ---------------------------------------------------------------------------
# Styled shop combo widget
# ---------------------------------------------------------------------------

class _ShopComboWidget(QWidget):
    index_changed      = Signal(int)
    new_shop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)

        # Picker frame
        picker = QFrame()
        picker.setFixedHeight(52)
        picker.setStyleSheet(f"""
            QFrame {{
                background: {_GREY_CARD};
                border: 1.5px solid {_GREY_BORDER};
                border-radius: 10px;
            }}
        """)
        pl = QHBoxLayout(picker)
        pl.setContentsMargins(12, 0, 12, 0)
        pl.setSpacing(8)

        icon = QLabel("🏪")
        icon.setStyleSheet("font-size: 18px; background: transparent; border: none;")
        pl.addWidget(icon)

        self.combo = QComboBox()
        self.combo.setFixedHeight(48)
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background: transparent;
                border: none;
                font-size: 14px;
                font-weight: 600;
                color: {_TEXT_DARK};
                padding: 0;
            }}
            QComboBox::drop-down {{ border: none; width: 0; }}
            QComboBox QAbstractItemView {{
                background: {_GREY_CARD};
                border: 1.5px solid {_GREY_BORDER};
                border-radius: 8px;
                selection-background-color: {_SAFE_BG};
                color: {_TEXT_DARK};
                font-size: 13px;
                padding: 4px;
            }}
        """)
        self.combo.currentIndexChanged.connect(self.index_changed)
        pl.addWidget(self.combo, 1)

        chev = QLabel("▾")
        chev.setStyleSheet(f"color: {_GREY_TEXT}; font-size: 13px; background: transparent; border: none;")
        pl.addWidget(chev)
        h.addWidget(picker, 1)

        new_btn = QPushButton("⊕  New shop")
        new_btn.setFixedHeight(52)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1.5px solid {_TEAL_ACCENT};
                border-radius: 10px;
                color: {_TEAL_BTN};
                font-size: 13px;
                font-weight: 700;
                padding: 0 14px;
            }}
            QPushButton:hover {{ background: {_SAFE_BG}; }}
        """)
        new_btn.clicked.connect(self.new_shop_requested)
        h.addWidget(new_btn)


# ---------------------------------------------------------------------------
# Left brand panel
# ---------------------------------------------------------------------------

class _BrandPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(340)
        self.setMaximumWidth(420)
        # App-wide QSS gives every QWidget a solid fill; override for feature rows (see _feature).
        self.setStyleSheet(
            """
            QWidget#loginBrandFeature,
            QWidget#loginBrandFeatureCol {
                background-color: transparent;
                border: none;
            }
            """
        )
        self._build()

    def _build(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(40, 36, 40, 32)
        v.setSpacing(0)

        # Logo row
        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        logo_icon = QLabel("🛒")
        logo_icon.setFixedSize(44, 44)
        logo_icon.setAlignment(Qt.AlignCenter)
        logo_icon.setStyleSheet(
            "background: rgba(255,255,255,0.12); border-radius: 10px;"
            " font-size: 20px; color: white;"
        )
        logo_row.addWidget(logo_icon)
        logo_name = QLabel(
            f"SmartStock <span style='color:{_TEAL_ACCENT};'>POS</span>"
        )
        logo_name.setTextFormat(Qt.RichText)
        logo_name.setStyleSheet("color: white; font-size: 18px; font-weight: 700;")
        logo_row.addWidget(logo_name)
        logo_row.addStretch()
        v.addLayout(logo_row)
        v.addSpacing(48)

        # Headline
        headline = QLabel(
            f"Run your business\n"
            f"<span style='color:{_TEAL_ACCENT};'>smarter.</span>"
        )
        headline.setTextFormat(Qt.RichText)
        headline.setWordWrap(True)
        headline.setStyleSheet(
            "color: white; font-size: 26px; font-weight: 800; line-height: 1.3;"
        )
        v.addWidget(headline)
        v.addSpacing(10)

        tagline = QLabel(
            "Powerful. Simple. Reliable.\nEverything you need in one place."
        )
        tagline.setWordWrap(True)
        tagline.setStyleSheet("color: rgba(255,255,255,0.65); font-size: 13px;")
        v.addWidget(tagline)
        v.addSpacing(32)

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: rgba(255,255,255,0.15);")
        div.setFixedHeight(1)
        v.addWidget(div)
        v.addSpacing(24)

        for emoji, title, desc in [
            ("⚡", "Fast & Efficient",
             "Speed up your sales and manage\neverything in real time."),
            ("📊", "Insights & Reports",
             "Track performance and grow\nyour business."),
            ("🛡", "Secure & Reliable",
             "Your data is protected\nwith top-grade security."),
        ]:
            v.addWidget(self._feature(emoji, title, desc))
            v.addSpacing(18)

        v.addStretch()

        foot_div = QFrame()
        foot_div.setFrameShape(QFrame.HLine)
        foot_div.setStyleSheet("color: rgba(255,255,255,0.15);")
        foot_div.setFixedHeight(1)
        v.addWidget(foot_div)
        v.addSpacing(14)

        footer = QLabel("♡  Built with passion for business owners")
        footer.setStyleSheet("color: rgba(255,255,255,0.40); font-size: 12px;")
        v.addWidget(footer)

    def _feature(self, emoji: str, title: str, desc: str) -> QWidget:
        row = QWidget()
        row.setObjectName("loginBrandFeature")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(14)
        h.setAlignment(Qt.AlignTop)

        icon = QLabel(emoji)
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            f"background: rgba(29,179,158,0.18); border-radius: 10px;"
            f" font-size: 18px; color: {_TEAL_ACCENT};"
        )
        h.addWidget(icon, 0, Qt.AlignTop)

        col = QWidget()
        col.setObjectName("loginBrandFeatureCol")
        cv = QVBoxLayout(col)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet("color: white; font-size: 14px; font-weight: 700;")
        cv.addWidget(t)
        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet("color: rgba(255,255,255,0.60); font-size: 12px;")
        cv.addWidget(d)
        h.addWidget(col, 1)
        return row

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(_TEAL_DARK))
        # Subtle dot-grid overlay
        p.setPen(QPen(QColor(255, 255, 255, 16), 1.5))
        step = 22
        for x in range(0, self.width(), step):
            for y in range(0, self.height(), step):
                p.drawPoint(x, y)
        p.end()
        super().paintEvent(event)


# ---------------------------------------------------------------------------
# Sign-in form panel (right, page 0)
# ---------------------------------------------------------------------------

class _SignInPanel(QWidget):
    login_requested          = Signal(str, str)
    new_shop_requested       = Signal()
    shop_index_changed       = Signal(int)
    create_account_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {_GREY_BG};")
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        content.setStyleSheet(f"background: {_GREY_BG};")
        v = QVBoxLayout(content)
        v.setContentsMargins(52, 48, 52, 48)
        v.setSpacing(0)
        v.setAlignment(Qt.AlignTop)

        # Header row
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title = QLabel("Welcome back!")
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 800; color: {_TEXT_DARK};"
        )
        title_col.addWidget(title)
        sub = QLabel("Sign in to continue")
        sub.setStyleSheet(f"font-size: 14px; color: {_GREY_TEXT};")
        title_col.addWidget(sub)
        hdr.addLayout(title_col, 1)

        lock = QLabel("🔒")
        lock.setFixedSize(56, 56)
        lock.setAlignment(Qt.AlignCenter)
        lock.setStyleSheet(
            f"background: {_SAFE_BG}; border-radius: 28px;"
            " font-size: 24px; border: 3px solid white;"
        )
        hdr.addWidget(lock, 0, Qt.AlignTop)
        v.addLayout(hdr)
        v.addSpacing(28)

        # Shop picker card
        shop_card = QFrame()
        shop_card.setStyleSheet(f"""
            QFrame {{
                background: {_GREY_CARD};
                border: 1.5px solid {_GREY_BORDER};
                border-radius: 14px;
            }}
        """)
        sc = QVBoxLayout(shop_card)
        sc.setContentsMargins(16, 14, 16, 14)
        sc.setSpacing(10)
        shop_lbl = QLabel("Select shop")
        shop_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {_GREY_TEXT};"
            " background: transparent; border: none;"
        )
        sc.addWidget(shop_lbl)
        self._shop_combo = _ShopComboWidget()
        self._shop_combo.index_changed.connect(self.shop_index_changed)
        self._shop_combo.new_shop_requested.connect(self.new_shop_requested)
        sc.addWidget(self._shop_combo)
        v.addWidget(shop_card)
        v.addSpacing(22)

        # Username
        self._user_entry = QLineEdit()
        self._user_entry.setPlaceholderText("Username")
        v.addWidget(_label("Username"))
        v.addSpacing(6)
        v.addWidget(_icon_frame("👤", self._user_entry, right_widget=self._kbd_icon()))
        v.addSpacing(14)

        # Password
        self._pass_entry = QLineEdit()
        self._pass_entry.setPlaceholderText("Enter password")
        self._pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self._eye_btn = QPushButton("👁")
        self._eye_btn.setFixedSize(36, 36)
        self._eye_btn.setFlat(True)
        self._eye_btn.setCursor(Qt.PointingHandCursor)
        self._eye_btn.setStyleSheet(
            f"font-size: 15px; background: transparent; border: none; color: {_GREY_TEXT};"
        )
        self._eye_btn.clicked.connect(self._toggle_pass)
        v.addWidget(_label("Password"))
        v.addSpacing(6)
        v.addWidget(_icon_frame("🔒", self._pass_entry, right_widget=self._eye_btn))
        v.addSpacing(10)

        # Remember me / forgot password row
        rm_row = QHBoxLayout()
        self._remember = QCheckBox("Remember me")
        self._remember.setStyleSheet(f"""
            QCheckBox {{
                font-size: 13px; color: {_GREY_LABEL}; spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 17px; height: 17px;
                border-radius: 5px;
                border: 1.5px solid {_GREY_BORDER};
                background: white;
            }}
            QCheckBox::indicator:checked {{
                background: {_TEAL_BTN};
                border-color: {_TEAL_BTN};
            }}
        """)
        rm_row.addWidget(self._remember)
        rm_row.addStretch()
        forgot = QPushButton("Forgot password?")
        forgot.setFlat(True)
        forgot.setCursor(Qt.PointingHandCursor)
        forgot.setStyleSheet(
            f"color: {_TEAL_ACCENT}; font-size: 13px; font-weight: 600;"
            " background: transparent; border: none; padding: 0;"
        )
        rm_row.addWidget(forgot)
        v.addLayout(rm_row)
        v.addSpacing(6)

        # Error
        self._error_lbl = QLabel("")
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setStyleSheet(
            f"color: {_ERROR_RED}; font-size: 12px; min-height: 16px;"
        )
        v.addWidget(self._error_lbl)
        v.addSpacing(4)

        # Sign in button
        sign_btn = _primary_button("➜  Sign in")
        sign_btn.clicked.connect(self._on_sign_in)
        v.addWidget(sign_btn)
        v.addSpacing(16)

        # "or" divider
        or_row = QHBoxLayout()
        ll = QFrame(); ll.setFrameShape(QFrame.HLine)
        ll.setStyleSheet(f"color: {_GREY_BORDER};")
        rl = QFrame(); rl.setFrameShape(QFrame.HLine)
        rl.setStyleSheet(f"color: {_GREY_BORDER};")
        ol = QLabel("or")
        ol.setFixedWidth(30)
        ol.setAlignment(Qt.AlignCenter)
        ol.setStyleSheet(f"color: {_GREY_TEXT}; font-size: 12px;")
        or_row.addWidget(ll, 1); or_row.addWidget(ol); or_row.addWidget(rl, 1)
        v.addLayout(or_row)
        v.addSpacing(16)

        # Create account button
        create_btn = _ghost_button("👤+  Create new account")
        create_btn.clicked.connect(self.create_account_requested)
        v.addWidget(create_btn)
        v.addSpacing(16)

        # Secure strip
        secure = QFrame()
        secure.setStyleSheet(
            f"QFrame {{ background: {_SAFE_BG}; border-radius: 10px; border: none; }}"
        )
        sl = QHBoxLayout(secure)
        sl.setContentsMargins(16, 10, 16, 10)
        sl.setAlignment(Qt.AlignCenter)
        sl.setSpacing(8)
        sh = QLabel("🛡")
        sh.setStyleSheet(f"font-size: 14px; color: {_TEAL_BTN}; background: transparent;")
        sl.addWidget(sh)
        st = QLabel("Secure login  •  Your data is safe with us")
        st.setStyleSheet(
            f"font-size: 12px; color: {_TEAL_BTN}; font-weight: 500; background: transparent;"
        )
        sl.addWidget(st)
        v.addWidget(secure)
        v.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._user_entry.returnPressed.connect(self._pass_entry.setFocus)
        self._pass_entry.returnPressed.connect(self._on_sign_in)

    def _kbd_icon(self) -> QLabel:
        lbl = QLabel("⌨")
        lbl.setFixedWidth(36)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"font-size: 14px; color: {_GREY_TEXT}; background: transparent;")
        return lbl

    def _toggle_pass(self) -> None:
        if self._pass_entry.echoMode() == QLineEdit.EchoMode.Password:
            self._pass_entry.setEchoMode(QLineEdit.EchoMode.Normal)
            self._eye_btn.setText("🙈")
        else:
            self._pass_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self._eye_btn.setText("👁")

    def _on_sign_in(self) -> None:
        self.login_requested.emit(
            self._user_entry.text(), self._pass_entry.text()
        )

    # --- public API ---
    def set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    def set_shop_list(self, labels: list[str], selected: int) -> None:
        c = self._shop_combo.combo
        c.blockSignals(True)
        c.clear()
        for l in labels:
            c.addItem(l)
        if c.count():
            c.setCurrentIndex(min(selected, c.count() - 1))
        c.blockSignals(False)

    def set_username(self, text: str) -> None:
        self._user_entry.setText(text)

    def clear_password(self) -> None:
        self._pass_entry.clear()


# ---------------------------------------------------------------------------
# Registration / shop-setup panel (right, page 1)
# ---------------------------------------------------------------------------

class _RegisterPanel(QWidget):
    register_requested  = Signal(str, str, str, str, str)
    back_requested      = Signal()
    new_shop_requested  = Signal()
    shop_index_changed  = Signal(int)
    save_name_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {_GREY_BG};")
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        content.setStyleSheet(f"background: {_GREY_BG};")
        v = QVBoxLayout(content)
        v.setContentsMargins(52, 48, 52, 48)
        v.setSpacing(0)
        v.setAlignment(Qt.AlignTop)

        title = QLabel("Shop setup")
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 800; color: {_TEXT_DARK};"
        )
        v.addWidget(title)
        sub = QLabel("Logo, shop, and business name for receipts.")
        sub.setStyleSheet(f"font-size: 14px; color: {_GREY_TEXT};")
        v.addWidget(sub)
        v.addSpacing(22)

        # Profile card
        prof = QFrame()
        prof.setStyleSheet(f"""
            QFrame {{
                background: {_GREY_CARD};
                border: 1.5px solid {_GREY_BORDER};
                border-radius: 14px;
            }}
        """)
        pv = QVBoxLayout(prof)
        pv.setContentsMargins(20, 18, 20, 18)
        pv.setSpacing(14)

        self._logo = ShopLogoLabel(prof, size=64, editable=True)
        pv.addWidget(self._logo, alignment=Qt.AlignCenter)

        # Shop combo row
        sr = QHBoxLayout()
        slbl = QLabel("Shop")
        slbl.setFixedWidth(96)
        slbl.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {_GREY_LABEL};"
        )
        sr.addWidget(slbl)
        self._shop_combo = _ShopComboWidget()
        self._shop_combo.index_changed.connect(self.shop_index_changed)
        self._shop_combo.new_shop_requested.connect(self.new_shop_requested)
        sr.addWidget(self._shop_combo, 1)
        pv.addLayout(sr)

        # Business name row
        br = QHBoxLayout()
        blbl = QLabel("Business name")
        blbl.setFixedWidth(96)
        blbl.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {_GREY_LABEL};"
        )
        br.addWidget(blbl)
        self._shop_entry = QLineEdit()
        self._shop_entry.setMinimumHeight(38)
        self._shop_entry.setStyleSheet(f"""
            QLineEdit {{
                background: {_GREY_BG};
                border: 1.5px solid {_GREY_BORDER};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 14px; font-weight: 700;
                color: {_TEXT_DARK};
            }}
            QLineEdit:focus {{ border-color: {_TEAL_ACCENT}; }}
        """)
        br.addWidget(self._shop_entry, 1)
        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(38)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1.5px solid {_GREY_BORDER};
                border-radius: 8px;
                font-size: 13px; font-weight: 600;
                color: {_TEAL_BTN}; padding: 0 12px;
            }}
            QPushButton:hover {{ background: {_SAFE_BG}; }}
        """)
        save_btn.clicked.connect(
            lambda: self.save_name_requested.emit(self._shop_entry.text())
        )
        br.addWidget(save_btn)
        pv.addLayout(br)

        v.addWidget(prof)
        v.addSpacing(18)

        # Account card
        acc = QFrame()
        acc.setStyleSheet(f"""
            QFrame {{
                background: {_GREY_CARD};
                border: 1.5px solid {_GREY_BORDER};
                border-radius: 14px;
            }}
        """)
        av = QVBoxLayout(acc)
        av.setContentsMargins(20, 18, 20, 18)
        av.setSpacing(10)

        at = QLabel("Create account")
        at.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_TEXT_DARK};"
        )
        av.addWidget(at)
        ah = QLabel("You'll be the owner of this shop.")
        ah.setStyleSheet(f"font-size: 13px; color: {_GREY_TEXT};")
        av.addWidget(ah)
        av.addSpacing(4)

        def _inp(ph: str, pw: bool = False) -> QLineEdit:
            w = QLineEdit()
            w.setPlaceholderText(ph)
            w.setMinimumHeight(42)
            if pw:
                w.setEchoMode(QLineEdit.EchoMode.Password)
            w.setStyleSheet(f"""
                QLineEdit {{
                    background: {_GREY_BG};
                    border: 1.5px solid {_GREY_BORDER};
                    border-radius: 8px;
                    padding: 0 12px;
                    font-size: 14px;
                    color: {_TEXT_DARK};
                }}
                QLineEdit:focus {{ border-color: {_TEAL_ACCENT}; }}
            """)
            return w

        def _frow(lbl_text: str, widget: QWidget) -> QHBoxLayout:
            row = QHBoxLayout()
            lbl = QLabel(lbl_text)
            lbl.setFixedWidth(110)
            lbl.setStyleSheet(
                f"font-size: 12px; font-weight: 600; color: {_GREY_LABEL};"
            )
            row.addWidget(lbl)
            row.addWidget(widget, 1)
            return row

        self._reg_full    = _inp("Full name")
        self._reg_user    = _inp("Username")
        self._reg_pass    = _inp("Password", pw=True)
        self._reg_confirm = _inp("Confirm password", pw=True)

        av.addLayout(_frow("Full name",        self._reg_full))
        av.addLayout(_frow("Username",         self._reg_user))
        av.addLayout(_frow("Password",         self._reg_pass))
        av.addLayout(_frow("Confirm password", self._reg_confirm))

        self._reg_error = QLabel("")
        self._reg_error.setWordWrap(True)
        self._reg_error.setStyleSheet(
            f"color: {_ERROR_RED}; font-size: 12px;"
        )
        av.addWidget(self._reg_error)

        create_btn = _primary_button("👤+  Create & sign in")
        create_btn.clicked.connect(self._on_register)
        av.addWidget(create_btn)

        back_btn = _ghost_button("← Back to sign in")
        back_btn.clicked.connect(self.back_requested)
        av.addWidget(back_btn)

        v.addWidget(acc)
        v.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._reg_full.returnPressed.connect(self._reg_user.setFocus)
        self._reg_user.returnPressed.connect(self._reg_pass.setFocus)
        self._reg_pass.returnPressed.connect(self._reg_confirm.setFocus)
        self._reg_confirm.returnPressed.connect(self._on_register)

    def _on_register(self) -> None:
        self.register_requested.emit(
            self._shop_entry.text(),
            self._reg_full.text(),
            self._reg_user.text(),
            self._reg_pass.text(),
            self._reg_confirm.text(),
        )

    # --- public API ---
    def set_error(self, msg: str) -> None:
        self._reg_error.setText(msg)

    def set_shop_name(self, name: str) -> None:
        self._shop_entry.setText(name)

    def set_shop_list(self, labels: list[str], selected: int) -> None:
        c = self._shop_combo.combo
        c.blockSignals(True)
        c.clear()
        for l in labels:
            c.addItem(l)
        if c.count():
            c.setCurrentIndex(min(selected, c.count() - 1))
        c.blockSignals(False)

    def refresh_logo(self) -> None:
        self._logo.refresh()


# ---------------------------------------------------------------------------
# ViewModel  (all business logic — unchanged from refactored version)
# ---------------------------------------------------------------------------

class LoginViewModel(QObject):
    shop_list_changed    = Signal(list, list, int)
    shop_context_changed = Signal()
    login_error_changed  = Signal(str)
    register_error_changed = Signal(str)
    authenticated        = Signal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._auth = AuthService()
        self._shop_combo_ids: list[str] = []

    @property
    def has_users(self) -> bool:
        return self._auth.has_any_users()

    @property
    def display_shop_name(self) -> str:
        return get_display_shop_name()

    def load_shops(self, select_id: str | None = None) -> None:
        shops = list_shops()
        labels, ids = shop_combo_entries(shops)
        self._shop_combo_ids = ids
        want = select_id if select_id is not None else get_current_shop_id()
        idx = ids.index(want) if want in ids else 0
        self.shop_list_changed.emit(labels, ids, min(idx, max(len(ids) - 1, 0)))

    def switch_shop(self, idx: int) -> bool:
        if idx < 0 or idx >= len(self._shop_combo_ids):
            return False
        sid = self._shop_combo_ids[idx]
        if sid == get_current_shop_id():
            return True
        try:
            open_shop_database(db, sid)
        except Exception:
            log.exception("Failed to open shop database id=%s", sid)
            return False
        self._refresh_auth()
        self.shop_context_changed.emit()
        return True

    def create_shop(self, name: str) -> str | None:
        name = name.strip()
        if not name:
            return None
        try:
            sid = create_new_shop(name)
            open_shop_database(db, sid)
        except Exception:
            log.exception("Failed to create shop name=%r", name)
            return None
        self._refresh_auth()
        self.shop_context_changed.emit()
        return sid

    def save_business_name(self, name: str) -> str | None:
        name = name.strip()
        if not name:
            return "Enter a business name."
        try:
            ShopSettings().set_shop_name(name)
        except ValueError as exc:
            return str(exc)
        return None

    def login(self, username: str, password: str) -> str | None:
        username = username.strip()
        if not username:
            return "Enter your username."
        self._auth.ensure_default_users()
        password = _clean_password(password)
        try:
            user = self._auth.authenticate(username, password)
        except Exception as exc:
            log.exception("Unexpected error during authenticate()")
            return f"Sign-in error: {exc}"
        if user:
            self.authenticated.emit(user)
            return None
        return self._diagnose_login_failure(username)

    def _diagnose_login_failure(self, username: str) -> str:
        try:
            tbl = db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            if tbl is None:
                return (
                    f"Users table missing. Delete {database_path()} and restart "
                    "(resets this shop only)."
                )
            exists = db.fetchone(
                "SELECT 1 FROM users WHERE lower(username) = lower(?) AND is_active = 1",
                (username,),
            )
        except sqlite3.OperationalError as exc:
            return f"Database error: {exc}"
        if exists is None:
            return (
                f'No active account found for "{username}". '
                "Check the username or ask your store owner."
            )
        return "Wrong password. Try again or use the correct account password."

    def complete_password_change(self, user: dict, new_password: str) -> dict | None:
        try:
            return self._auth.complete_first_login_password_change(
                user, new_password=new_password
            )
        except ValueError:
            log.exception("Password change rejected")
            return None

    def register(
        self, shop_name: str, full_name: str,
        username: str, password: str, confirm: str,
    ) -> str | None:
        shop_name = shop_name.strip()
        full_name = full_name.strip()
        username  = username.strip()
        password  = _clean_password(password)
        confirm   = _clean_password(confirm)
        if not shop_name: return "Enter a business name."
        if not full_name: return "Enter your full name."
        if not username:  return "Choose a username."
        if len(password) < 4: return "Password must be at least 4 characters."
        if password != confirm: return "Passwords do not match."
        try:
            user = self._auth.register_new_shop(
                shop_name=shop_name, full_name=full_name,
                username=username, password=password,
            )
        except ValueError as exc:
            return str(exc)
        except Exception as exc:
            log.exception("Unexpected error during register_new_shop()")
            return f"Could not register: {exc}"
        self.authenticated.emit(user)
        return None

    def _refresh_auth(self) -> None:
        self._auth = AuthService()


# ---------------------------------------------------------------------------
# ChangePasswordDialog (unchanged logic)
# ---------------------------------------------------------------------------

class ChangePasswordDialog(QDialog):
    def __init__(
        self, vm: LoginViewModel, user: dict, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._vm = vm
        self._user = user
        self._result_user: dict | None = None
        self.setWindowTitle("Change password")
        self.setModal(True)
        root = QVBoxLayout(self)
        hint = QLabel("You must change your password before entering the app.")
        hint.setWordWrap(True)
        root.addWidget(hint)
        form = QFormLayout()
        self._new_pw = QLineEdit()
        self._new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_pw = QLineEdit()
        self._confirm_pw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("New password", self._new_pw)
        form.addRow("Confirm password", self._confirm_pw)
        root.addLayout(form)
        self._err = QLabel("")
        self._err.setObjectName("errorText")
        self._err.setWordWrap(True)
        root.addWidget(self._err)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._new_pw.returnPressed.connect(self._confirm_pw.setFocus)
        self._confirm_pw.returnPressed.connect(self._on_accept)

    def _on_accept(self) -> None:
        self._err.setText("")
        p1 = _clean_password(self._new_pw.text())
        p2 = _clean_password(self._confirm_pw.text())
        if len(p1.strip()) < 4:
            self._err.setText("New password must be at least 4 characters.")
            return
        if p1 != p2:
            self._err.setText("Passwords do not match.")
            return
        updated = self._vm.complete_password_change(self._user, p1)
        if updated is None:
            self._err.setText("Password change failed. Please try again.")
            return
        self._result_user = updated
        super().accept()

    @property
    def updated_user(self) -> dict | None:
        return self._result_user


# ---------------------------------------------------------------------------
# LoginView — outer shell
# ---------------------------------------------------------------------------

class LoginView(QWidget):
    """Two-panel login screen: dark teal brand panel + white form panel."""

    def __init__(
        self, main_window: QWidget, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._main = main_window
        self._vm = LoginViewModel(self)
        self._syncing_shop_combo = False
        self._did_entrance_fade = False

        self._build_ui()
        self._connect_signals()
        self._vm.load_shops()
        self._sync_ui_to_shop()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._brand = _BrandPanel()
        root.addWidget(self._brand)

        self._signin_panel   = _SignInPanel()
        self._register_panel = _RegisterPanel()

        self._stack = QStackedWidget()
        self._stack.addWidget(self._signin_panel)    # 0
        self._stack.addWidget(self._register_panel)  # 1
        root.addWidget(self._stack, 1)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        # ViewModel → UI
        self._vm.shop_list_changed.connect(self._on_shop_list_changed)
        self._vm.shop_context_changed.connect(self._sync_ui_to_shop)
        self._vm.login_error_changed.connect(self._signin_panel.set_error)
        self._vm.register_error_changed.connect(self._register_panel.set_error)
        self._vm.authenticated.connect(self._on_authenticated)

        # Sign-in panel
        self._signin_panel.login_requested.connect(self._on_login)
        self._signin_panel.new_shop_requested.connect(self._on_new_shop)
        self._signin_panel.shop_index_changed.connect(self._on_shop_index_changed)
        self._signin_panel.create_account_requested.connect(
            lambda: self._stack.setCurrentIndex(1)
        )

        # Register panel
        self._register_panel.register_requested.connect(self._on_register)
        self._register_panel.back_requested.connect(
            lambda: self._stack.setCurrentIndex(0)
        )
        self._register_panel.new_shop_requested.connect(self._on_new_shop)
        self._register_panel.shop_index_changed.connect(self._on_shop_index_changed)
        self._register_panel.save_name_requested.connect(self._on_save_business_name)

    # ------------------------------------------------------------------
    # ViewModel → UI
    # ------------------------------------------------------------------

    def _on_shop_list_changed(
        self, labels: list[str], ids: list[str], selected: int
    ) -> None:
        with self._block_combo_signals():
            self._signin_panel.set_shop_list(labels, selected)
            self._register_panel.set_shop_list(labels, selected)

    def _sync_ui_to_shop(self) -> None:
        self._signin_panel.set_error("")
        self._register_panel.set_error("")
        self._register_panel.set_shop_name(self._vm.display_shop_name)
        self._register_panel.refresh_logo()
        self._signin_panel.set_username("admin" if self._vm.has_users else "")
        self._stack.setCurrentIndex(0 if self._vm.has_users else 1)

    def _on_authenticated(self, user: dict) -> None:
        if user.get("must_change_password"):
            dlg = ChangePasswordDialog(self._vm, user, parent=self.window())
            if dlg.exec() != QDialog.DialogCode.Accepted or dlg.updated_user is None:
                self._signin_panel.set_error(
                    "Password change is required before you can continue."
                )
                return
            user = dlg.updated_user
        self._signin_panel.clear_password()
        self._main.enter_app(user)

    # ------------------------------------------------------------------
    # User-action slots
    # ------------------------------------------------------------------

    def _on_shop_index_changed(self, idx: int) -> None:
        if self._syncing_shop_combo:
            return
        # Sync the opposite panel's combo
        with self._block_combo_signals():
            if self._stack.currentIndex() == 0:
                other = self._register_panel._shop_combo.combo
            else:
                other = self._signin_panel._shop_combo.combo
            if other.currentIndex() != idx and 0 <= idx < other.count():
                other.setCurrentIndex(idx)
        if not self._vm.switch_shop(idx):
            warning_message(
                self.window(), "Switch shop", "Could not open the selected shop."
            )
            self._vm.load_shops()

    def _on_new_shop(self) -> None:
        text, ok = QInputDialog.getText(
            self.window(), "New shop", "Business / shop name:"
        )
        if not ok:
            return
        sid = self._vm.create_shop(text or "")
        if sid is None:
            warning_message(self.window(), "New shop", "Could not create the shop.")
            return
        self._vm.load_shops(select_id=sid)

    def _on_save_business_name(self, name: str) -> None:
        err = self._vm.save_business_name(name)
        if err:
            warning_message(self.window(), "Business name", err)

    def _on_login(self, username: str, password: str) -> None:
        self._signin_panel.set_error("")
        err = self._vm.login(username, password)
        if err:
            self._signin_panel.set_error(err)

    def _on_register(
        self, shop: str, full: str, user: str, pw: str, confirm: str
    ) -> None:
        self._register_panel.set_error("")
        err = self._vm.register(shop, full, user, pw, confirm)
        if err:
            self._register_panel.set_error(err)

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._register_panel.refresh_logo()
        self._register_panel.set_shop_name(self._vm.display_shop_name)
        self._vm.load_shops()
        if not self._did_entrance_fade:
            self._did_entrance_fade = True
            # Lazy import prevents circular dependency with motion module
            from app.ui_qt.motion_qt import fade_in_widget
            fade_in_widget(self, 260)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @contextmanager
    def _block_combo_signals(self) -> Generator[None, None, None]:
        self._syncing_shop_combo = True
        try:
            yield
        finally:
            self._syncing_shop_combo = False
