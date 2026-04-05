"""Global Qt stylesheets — modern dark/light themes (brand-aligned)."""

from __future__ import annotations

from app.ui.theme_tokens import TOKENS

# Brand primary (single source: ``theme_tokens.TOKENS``)
_ACCENT = TOKENS.PRIMARY
_ACCENT_HOVER = TOKENS.PRIMARY_HOVER
_ACCENT_MUTED = TOKENS.PRIMARY_MUTED

_DARK_QSS = f"""
/* ---- Base ---- */
QMainWindow, QWidget {{
    background-color: #070b11;
    color: #e8eaef;
    font-family: "Segoe UI", "SF Pro Text", system-ui, sans-serif;
    font-size: 13px;
    selection-background-color: {_ACCENT};
    selection-color: #ffffff;
}}

/* QLabel: transparent so text sits on the parent surface (cards, rails) instead of a separate fill */
QLabel {{
    background-color: transparent;
}}

QToolTip {{
    background-color: #131b26;
    color: #e8eaef;
    border: 1px solid #304560;
    border-radius: 8px;
    padding: 8px 10px;
}}

QMenu {{
    background-color: #101820;
    border: 1px solid #304560;
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 10px 28px 10px 14px;
    border-radius: 8px;
}}
QMenu::item:selected {{
    background-color: #1e2a3c;
}}

QScrollArea, QAbstractScrollArea {{
    border: none;
    background-color: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ---- Shell: sidebar ---- */
QFrame#sidebarRail {{
    background-color: #0c121c;
    border: 1px solid #182633;
    border-radius: 16px;
}}

QListWidget {{
    background-color: transparent;
    border: none;
    border-radius: 12px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 12px 14px 12px 16px;
    border-radius: 10px;
    margin: 3px 4px;
    border-left: 3px solid transparent;
    color: #b4bcc8;
}}
QListWidget::item:selected {{
    background-color: #161f2e;
    color: #f0f4f8;
    border-left: 3px solid {_ACCENT};
    font-weight: 600;
}}
QListWidget::item:hover:!selected {{
    background-color: #151c28;
    color: #dce2eb;
}}

/* ---- Top bar ---- */
QFrame#topBar {{
    background-color: #0c121c;
    border: none;
    border-bottom: 1px solid #182633;
}}
QFrame#topBar QLabel {{
    color: #c5cdd8;
    font-size: 13px;
}}

QFrame#appFooter {{
    background-color: #070b11;
    border-top: 1px solid #182633;
}}
QLabel#appFooterText {{
    color: #8b95a8;
    font-size: 11px;
}}

QWidget#contentHost {{
    background-color: #070b11;
}}

QLabel#pageTitle {{
    font-size: 22px;
    font-weight: 700;
    color: #f0f4f8;
    letter-spacing: -0.4px;
}}
QLabel#pageSubtitle {{
    font-size: 13px;
    color: #8b95a8;
}}
QLabel#sidebarBrandName {{
    font-size: 15px;
    font-weight: 700;
    color: #f0f4f8;
}}
QLabel#sidebarBrandTag {{
    font-size: 11px;
    color: #8b95a8;
}}
QLabel#topBarUser {{
    color: #c5cdd8;
    font-size: 13px;
    max-width: 220px;
}}
QLabel#userAvatar {{
    background-color: #153545;
    color: #e8eaef;
    border-radius: 21px;
    font-weight: 700;
    font-size: 15px;
    border: 2px solid #304560;
}}
QLineEdit#globalSearch {{
    background-color: #090f17;
    border: 1px solid #304560;
    border-radius: 12px;
    padding: 10px 14px;
    min-height: 20px;
}}
QPushButton#iconButton {{
    background-color: #1c2938;
    border: 1px solid #304560;
    border-radius: 12px;
    font-size: 16px;
    padding: 0;
}}
QPushButton#iconButton:hover {{
    background-color: #1e2a3c;
}}

QListWidget#sidebarNav {{
    background-color: transparent;
}}

QLabel#heroMetric {{
    font-size: 36px;
    font-weight: 700;
    color: #f5f7fa;
    letter-spacing: -1px;
}}
QFrame#miniKpiCard {{
    background-color: #121b2a;
    border: 1px solid #283849;
    border-radius: 14px;
}}
QLabel#miniKpiTitle {{
    font-size: 12px;
    color: #8b95a8;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
QLabel#miniKpiValue {{
    font-size: 20px;
    font-weight: 700;
    color: #f0f4f8;
}}
QFrame#chartPlaceholder {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #182436, stop:0.5 #131d2c, stop:1 #101820);
    border: 1px solid #283849;
    border-radius: 14px;
}}
QLabel#chartPlaceholderTitle {{
    font-size: 14px;
    font-weight: 600;
    color: #b4bcc8;
}}
QFrame#donutPlaceholder {{
    background-color: #090f17;
    border: 3px solid {_ACCENT};
    border-radius: 60px;
}}
QLabel#donutValue {{
    font-size: 22px;
    font-weight: 700;
    color: #f0f4f8;
}}
QPushButton#pillTab {{
    background-color: transparent;
    color: #8b95a8;
    border: 1px solid #304560;
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#pillTab:hover {{
    background-color: #161f2e;
    color: #dce2eb;
}}
QPushButton#pillTab:checked {{
    background-color: #153545;
    color: #ffffff;
    border-color: {_ACCENT};
}}

/* ---- Typography ---- */
QLabel#title {{
    font-size: 24px;
    font-weight: 700;
    color: #f0f4f8;
    letter-spacing: -0.3px;
}}
QLabel#section {{
    font-size: 14px;
    font-weight: 600;
    color: #dce2eb;
}}
QLabel#muted {{
    color: #8b95a8;
    font-size: 12px;
}}
QLabel#kpiValue {{
    font-size: 22px;
    font-weight: 700;
    color: #f5f7fa;
    letter-spacing: -0.5px;
}}
QLabel#kpiValueSm {{
    font-size: 16px;
    font-weight: 700;
    color: #f0f4f8;
}}
QLabel#heroTime {{
    font-size: 22px;
    font-weight: 700;
    color: {_ACCENT};
    letter-spacing: -0.3px;
}}
QLabel#pillNeutral {{
    background-color: #1c2938;
    color: #c5cdd8;
    border: 1px solid #304560;
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#errorText {{
    color: #f07178;
    font-size: 12px;
}}
QLabel#statusOk {{
    color: #7fd99a;
    font-weight: 600;
}}
QLabel#statusBad {{
    color: #f07178;
    font-weight: 600;
}}

/* ---- Cards ---- */
QFrame#card {{
    background-color: #121b2a;
    border: 1px solid #283849;
    border-radius: 14px;
}}
QFrame#cardWarning {{
    background-color: #121b2a;
    border: 1px solid #c4a035;
    border-radius: 14px;
}}
QFrame#loginCard {{
    background-color: #121b2a;
    border: 1px solid #2b3648;
    border-radius: 18px;
}}

/* ---- Buttons ---- */
QPushButton {{
    background-color: #1c2938;
    color: #e8eaef;
    border: 1px solid #304560;
    border-radius: 10px;
    padding: 10px 18px;
    min-height: 22px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: #1e2a3c;
    border-color: #435a73;
}}
QPushButton:pressed {{
    background-color: #111920;
}}
QPushButton:disabled {{
    color: #5c6570;
    border-color: #1e2a3c;
}}

QPushButton#primary {{
    background-color: {_ACCENT};
    color: #ffffff;
    border: 1px solid {_ACCENT_HOVER};
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background-color: {_ACCENT_HOVER};
    border-color: #4db3d4;
}}
QPushButton#primary:pressed {{
    background-color: {_ACCENT_MUTED};
}}

QPushButton#ghost {{
    background-color: transparent;
    color: #b4bcc8;
    border: 1px solid #304560;
}}
QPushButton#ghost:hover {{
    background-color: #161f2e;
    color: #e8eaef;
    border-color: #435a73;
}}

QPushButton#danger {{
    background-color: #5c2b35;
    color: #f5c6cb;
    border: 1px solid #8b3a48;
}}
QPushButton#danger:hover {{
    background-color: #702f3a;
}}

QPushButton#success {{
    background-color: #1e4d2e;
    color: #b8f0c8;
    border: 1px solid #2d6a42;
}}
QPushButton#success:hover {{
    background-color: #256338;
}}

/* ---- Inputs ---- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: #090f17;
    border: 1px solid #304560;
    border-radius: 10px;
    padding: 9px 12px;
    min-height: 22px;
    color: #e8eaef;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {_ACCENT};
    background-color: #12161c;
}}
QComboBox::drop-down {{
    border: none;
    width: 32px;
}}
QComboBox QAbstractItemView {{
    background-color: #101820;
    selection-background-color: #1e2a3c;
    border: 1px solid #304560;
    border-radius: 8px;
    padding: 4px;
}}

/* ---- Tables ---- */
QTableWidget {{
    background-color: #090f17;
    alternate-background-color: #0d151f;
    gridline-color: #182633;
    border: 1px solid #283849;
    border-radius: 14px;
}}
QTableWidget::item {{
    padding: 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: #1a3040;
    color: #f0f4f8;
}}
QTableWidget::item:hover:!selected {{
    background-color: #141d2a;
}}
QHeaderView::section {{
    background-color: #121b2a;
    color: #b4bcc8;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #283849;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}

/* ---- Scrollbars ---- */
QScrollBar:vertical {{
    background: #090f17;
    width: 10px;
    margin: 4px 2px 4px 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: #304560;
    min-height: 36px;
    border-radius: 5px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: #435a73;
}}
QScrollBar:horizontal {{
    background: #090f17;
    height: 10px;
    margin: 0 4px 2px 4px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: #304560;
    border-radius: 5px;
    margin: 2px;
}}

/* ---- Misc ---- */
QCheckBox, QRadioButton {{
    spacing: 10px;
    color: #dce2eb;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #435a73;
    background-color: #090f17;
}}
QRadioButton::indicator {{
    border-radius: 9px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {_ACCENT};
    border-color: {_ACCENT_HOVER};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {_ACCENT};
}}

QDialog {{
    background-color: #070b11;
}}
QTextEdit, QPlainTextEdit {{
    background-color: #090f17;
    border: 1px solid #304560;
    border-radius: 10px;
    padding: 10px;
    color: #e8eaef;
}}

QDialogButtonBox QPushButton {{
    min-width: 88px;
}}

/* Shop logo drop target */
QLabel#shopLogo[logoState="image"] {{
    border: 2px solid #304560;
    border-radius: 999px;
    background-color: #121b2a;
}}
QLabel#shopLogo[logoState="empty"] {{
    border: 2px dashed #435a73;
    border-radius: 999px;
    color: #8b95a8;
    font-weight: 700;
    background-color: #090f17;
}}
"""

_LIGHT_QSS = f"""
QMainWindow, QWidget {{
    background-color: #e8ecf3;
    color: #1a1f28;
    font-family: "Segoe UI", "SF Pro Text", system-ui, sans-serif;
    font-size: 13px;
    selection-background-color: {_ACCENT};
    selection-color: #ffffff;
}}

QLabel {{
    background-color: transparent;
}}

QToolTip {{
    background-color: #ffffff;
    color: #1a1f28;
    border: 1px solid #d1dae6;
    border-radius: 8px;
    padding: 8px 10px;
}}

QMenu {{
    background-color: #ffffff;
    border: 1px solid #d1dae6;
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 10px 28px 10px 14px;
    border-radius: 8px;
}}
QMenu::item:selected {{
    background-color: #eef3f7;
}}

QScrollArea, QAbstractScrollArea {{
    border: none;
    background-color: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

QFrame#sidebarRail {{
    background-color: #ffffff;
    border: 1px solid #d1dae6;
    border-radius: 16px;
}}

QListWidget {{
    background-color: transparent;
    border: none;
    border-radius: 12px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 12px 14px 12px 16px;
    border-radius: 10px;
    margin: 3px 4px;
    border-left: 3px solid transparent;
    color: #4a5568;
}}
QListWidget::item:selected {{
    background-color: #e8f4f8;
    color: #0d3d4d;
    border-left: 3px solid {_ACCENT};
    font-weight: 600;
}}
QListWidget::item:hover:!selected {{
    background-color: #eef2f7;
    color: #2d3748;
}}

QFrame#topBar {{
    background-color: #ffffff;
    border: none;
    border-bottom: 1px solid #d1dae6;
}}
QFrame#topBar QLabel {{
    color: #4a5568;
    font-size: 13px;
}}

QFrame#appFooter {{
    background-color: #e8ecf3;
    border-top: 1px solid #d1dae6;
}}
QLabel#appFooterText {{
    color: #6b7280;
    font-size: 11px;
}}

QWidget#contentHost {{
    background-color: #e8ecf3;
}}

QLabel#pageTitle {{
    font-size: 22px;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.4px;
}}
QLabel#pageSubtitle {{
    font-size: 13px;
    color: #6b7280;
}}
QLabel#sidebarBrandName {{
    font-size: 15px;
    font-weight: 700;
    color: #111827;
}}
QLabel#sidebarBrandTag {{
    font-size: 11px;
    color: #6b7280;
}}
QLabel#topBarUser {{
    color: #4b5563;
    font-size: 13px;
    max-width: 220px;
}}
QLabel#userAvatar {{
    background-color: #dbeafe;
    color: #1e40af;
    border-radius: 21px;
    font-weight: 700;
    font-size: 15px;
    border: 2px solid #bfdbfe;
}}
QLineEdit#globalSearch {{
    background-color: #ffffff;
    border: 1px solid #c5cdd8;
    border-radius: 12px;
    padding: 10px 14px;
    min-height: 20px;
}}
QPushButton#iconButton {{
    background-color: #ffffff;
    border: 1px solid #d1dae6;
    border-radius: 12px;
    font-size: 16px;
    padding: 0;
}}
QPushButton#iconButton:hover {{
    background-color: #f7f9fc;
}}

QListWidget#sidebarNav {{
    background-color: transparent;
}}

QLabel#heroMetric {{
    font-size: 36px;
    font-weight: 700;
    color: #111827;
    letter-spacing: -1px;
}}
QFrame#miniKpiCard {{
    background-color: #ffffff;
    border: 1px solid #d1dae6;
    border-radius: 14px;
}}
QLabel#miniKpiTitle {{
    font-size: 12px;
    color: #6b7280;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
QLabel#miniKpiValue {{
    font-size: 20px;
    font-weight: 700;
    color: #111827;
}}
QFrame#chartPlaceholder {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #edf3f9, stop:0.5 #e4f0f7, stop:1 #ffffff);
    border: 1px solid #d1dae6;
    border-radius: 14px;
}}
QLabel#chartPlaceholderTitle {{
    font-size: 14px;
    font-weight: 600;
    color: #4b5563;
}}
QFrame#donutPlaceholder {{
    background-color: #ffffff;
    border: 3px solid {_ACCENT};
    border-radius: 60px;
}}
QLabel#donutValue {{
    font-size: 22px;
    font-weight: 700;
    color: #111827;
}}
QPushButton#pillTab {{
    background-color: transparent;
    color: #6b7280;
    border: 1px solid #d1d5db;
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#pillTab:hover {{
    background-color: #f3f4f6;
    color: #111827;
}}
QPushButton#pillTab:checked {{
    background-color: #e8f4f8;
    color: #0d3d4d;
    border-color: {_ACCENT};
}}

QLabel#title {{
    font-size: 24px;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.3px;
}}
QLabel#section {{
    font-size: 14px;
    font-weight: 600;
    color: #2d3748;
}}
QLabel#muted {{
    color: #6b7280;
    font-size: 12px;
}}
QLabel#kpiValue {{
    font-size: 22px;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.5px;
}}
QLabel#kpiValueSm {{
    font-size: 16px;
    font-weight: 700;
    color: #1a1f28;
}}
QLabel#heroTime {{
    font-size: 22px;
    font-weight: 700;
    color: {_ACCENT};
    letter-spacing: -0.3px;
}}
QLabel#pillNeutral {{
    background-color: #eef3f7;
    color: #374151;
    border: 1px solid #d1dae6;
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#errorText {{
    color: #b91c1c;
    font-size: 12px;
}}
QLabel#statusOk {{
    color: #15803d;
    font-weight: 600;
}}
QLabel#statusBad {{
    color: #b91c1c;
    font-weight: 600;
}}

QFrame#card {{
    background-color: #ffffff;
    border: 1px solid #d1dae6;
    border-radius: 14px;
}}
QFrame#cardWarning {{
    background-color: #fffbeb;
    border: 1px solid #f59e0b;
    border-radius: 14px;
}}
QFrame#loginCard {{
    background-color: #ffffff;
    border: 1px solid #d1dae6;
    border-radius: 18px;
}}

QPushButton {{
    background-color: #ffffff;
    color: #1a1f28;
    border: 1px solid #c5cdd8;
    border-radius: 10px;
    padding: 10px 18px;
    min-height: 22px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: #f7f9fc;
    border-color: #9ca3af;
}}
QPushButton:pressed {{
    background-color: #e8ecf3;
}}
QPushButton:disabled {{
    color: #9ca3af;
    border-color: #e5e7eb;
}}

QPushButton#primary {{
    background-color: {_ACCENT};
    color: #ffffff;
    border: 1px solid {_ACCENT};
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background-color: {_ACCENT_HOVER};
    border-color: {_ACCENT_HOVER};
}}
QPushButton#primary:pressed {{
    background-color: #256b87;
}}

QPushButton#ghost {{
    background-color: transparent;
    color: #4b5563;
    border: 1px solid #d1d5db;
}}
QPushButton#ghost:hover {{
    background-color: #f3f4f6;
    color: #111827;
}}

QPushButton#danger {{
    background-color: #fef2f2;
    color: #991b1b;
    border: 1px solid #fecaca;
}}
QPushButton#danger:hover {{
    background-color: #fee2e2;
}}

QPushButton#success {{
    background-color: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
}}
QPushButton#success:hover {{
    background-color: #d1fae5;
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: #ffffff;
    border: 1px solid #c5cdd8;
    border-radius: 10px;
    padding: 9px 12px;
    min-height: 22px;
    color: #1a1f28;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {_ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 32px;
}}
QComboBox QAbstractItemView {{
    background-color: #ffffff;
    selection-background-color: #e8f4f8;
    border: 1px solid #d1dae6;
    border-radius: 8px;
    padding: 4px;
}}

QTableWidget {{
    background-color: #ffffff;
    alternate-background-color: #f4f7fb;
    gridline-color: #e5e7eb;
    border: 1px solid #d1dae6;
    border-radius: 14px;
}}
QTableWidget::item {{
    padding: 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: #dbeafe;
    color: #1e3a5f;
}}
QTableWidget::item:hover:!selected {{
    background-color: #e4eaf2;
}}
QHeaderView::section {{
    background-color: #f4f7fb;
    color: #4b5563;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #e5e7eb;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}

QScrollBar:vertical {{
    background: #e4eaf2;
    width: 10px;
    margin: 4px 2px 4px 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: #cbd5e1;
    min-height: 36px;
    border-radius: 5px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94a3b8;
}}
QScrollBar:horizontal {{
    background: #e4eaf2;
    height: 10px;
    margin: 0 4px 2px 4px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: #cbd5e1;
    border-radius: 5px;
    margin: 2px;
}}

QCheckBox, QRadioButton {{
    spacing: 10px;
    color: #374151;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #9ca3af;
    background-color: #ffffff;
}}
QRadioButton::indicator {{
    border-radius: 9px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {_ACCENT};
    border-color: {_ACCENT};
}}

QDialog {{
    background-color: #e8ecf3;
}}
QTextEdit, QPlainTextEdit {{
    background-color: #ffffff;
    border: 1px solid #c5cdd8;
    border-radius: 10px;
    padding: 10px;
    color: #1a1f28;
}}

QDialogButtonBox QPushButton {{
    min-width: 88px;
}}

QLabel#shopLogo[logoState="image"] {{
    border: 2px solid #d1dae6;
    border-radius: 999px;
    background-color: #ffffff;
}}
QLabel#shopLogo[logoState="empty"] {{
    border: 2px dashed #9ca3af;
    border-radius: 999px;
    color: #6b7280;
    font-weight: 700;
    background-color: #f4f7fb;
}}
"""


def get_qt_stylesheet(appearance: str) -> str:
    """Return full application QSS for ``dark`` or ``light``."""
    if (appearance or "").lower() == "light":
        return _LIGHT_QSS
    return _DARK_QSS


# Default export for imports that expect a single string (dark).
APPLIED_STYLESHEET = _DARK_QSS
