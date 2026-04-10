"""Global Qt stylesheets — modern dark/light themes (brand-aligned)."""

from __future__ import annotations

from app.ui.theme_tokens import (
    CTK_CARD_BORDER,
    CTK_CARD_BORDER_STRONG,
    CTK_NAV_BORDER_ACCENT,
    CTK_NAV_HOVER_SURFACE,
    CTK_NAV_TEXT_MUTED,
    TOKENS,
    SURFACE_BASE_DARK,
    SURFACE_BASE_LIGHT,
    SURFACE_CARD_DARK,
    SURFACE_CARD_LIGHT,
    SURFACE_ELEVATED_DARK,
    SURFACE_ELEVATED_LIGHT,
)

_ACCENT = TOKENS.PRIMARY
_ACCENT_HOVER = TOKENS.PRIMARY_HOVER
_ACCENT_MUTED = TOKENS.PRIMARY_MUTED
_SUCCESS = TOKENS.SUCCESS
_SUCCESS_HOVER = TOKENS.SUCCESS_HOVER

_SBD = SURFACE_BASE_DARK
_SCD = SURFACE_CARD_DARK
_SED = SURFACE_ELEVATED_DARK
_SBL = SURFACE_BASE_LIGHT
_SCL = SURFACE_CARD_LIGHT
_SEL = SURFACE_ELEVATED_LIGHT

_BC_D = CTK_CARD_BORDER[1]
_BC_D_S = CTK_CARD_BORDER_STRONG[1]
_BC_L = CTK_CARD_BORDER[0]
_BC_L_S = CTK_CARD_BORDER_STRONG[0]

_NAV_MUTED_FG_D = CTK_NAV_TEXT_MUTED[1]
_NAV_HOVER_BG_D = CTK_NAV_HOVER_SURFACE[1]
_NAV_ACCENT_D = CTK_NAV_BORDER_ACCENT[1]

_NAV_MUTED_FG_L = CTK_NAV_TEXT_MUTED[0]
_NAV_HOVER_BG_L = CTK_NAV_HOVER_SURFACE[0]
_NAV_ACCENT_L = CTK_NAV_BORDER_ACCENT[0]

_DARK_QSS = f"""
/* ---- Base ---- */
QMainWindow, QWidget {{
    background-color: {_SBD};
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
    background-color: {_SCD};
    color: #e8eaef;
    border: 1px solid {_BC_D_S};
    border-radius: 8px;
    padding: 8px 10px;
}}

QMenu {{
    background-color: {_SCD};
    border: 1px solid {_BC_D_S};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 10px 28px 10px 14px;
    border-radius: 8px;
}}
QMenu::item:selected {{
    background-color: {_SED};
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
    background-color: {_SCD};
    border: 1px solid {_BC_D};
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
    color: {_NAV_MUTED_FG_D};
}}
QListWidget::item:selected {{
    background-color: {_SED};
    color: #f8fafc;
    border-left: 3px solid {_NAV_ACCENT_D};
    font-weight: 600;
}}
QListWidget::item:hover:!selected {{
    background-color: {_NAV_HOVER_BG_D};
    color: #f1f5f9;
}}

/* ---- Top bar ---- */
QFrame#topBar {{
    background-color: {_SCD};
    border: none;
    border-bottom: 1px solid {_BC_D};
}}
QFrame#topBar QLabel {{
    color: #c5cdd8;
    font-size: 13px;
}}

QFrame#appFooter {{
    background-color: {_SBD};
    border-top: 1px solid {_BC_D};
}}
QLabel#appFooterText {{
    color: #8b95a8;
    font-size: 11px;
}}

QWidget#contentHost {{
    background-color: {_SBD};
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
    background-color: {_ACCENT_MUTED};
    color: #e8eaef;
    border-radius: 21px;
    font-weight: 700;
    font-size: 15px;
    border: 2px solid {_BC_D_S};
}}
QLineEdit#globalSearch {{
    background-color: {_SED};
    border: 1px solid {_BC_D_S};
    border-radius: 12px;
    padding: 10px 14px;
    min-height: 20px;
}}
QPushButton#iconButton {{
    background-color: {_SED};
    border: 1px solid {_BC_D_S};
    border-radius: 12px;
    font-size: 16px;
    padding: 0;
}}
QPushButton#iconButton:hover {{
    background-color: {_SED};
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
    background-color: {_SED};
    border: 1px solid {_BC_D};
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
QWidget#dashboardSalesChart {{
    background-color: transparent;
    min-height: 260px;
}}
QLabel#chartPlaceholderTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {_ACCENT_HOVER};
    letter-spacing: 0.02em;
}}
QFrame#donutPlaceholder {{
    background-color: {_SED};
    border: 3px solid {_ACCENT};
    border-radius: 60px;
}}
QLabel#donutValue {{
    font-size: 22px;
    font-weight: 700;
    color: #f0f4f8;
}}
QLabel#dashboardActionBadge {{
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    background-color: transparent;
}}
QLabel#dashboardActionName {{
    font-size: 11px;
    font-weight: 600;
    color: #f1f5f9;
    background-color: transparent;
}}
QFrame#dashboardActionTileExpiring {{
    background-color: {_SCD};
    border: 1px solid #92400e;
    border-radius: 12px;
    border-left: 4px solid #fbbf24;
}}
QFrame#dashboardActionTileLow {{
    background-color: {_SCD};
    border: 1px solid {_BC_D};
    border-radius: 12px;
    border-left: 4px solid {_ACCENT};
}}
QPushButton#pillTab {{
    background-color: transparent;
    color: #8b95a8;
    border: 1px solid {_BC_D_S};
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#pillTab:hover {{
    background-color: {_NAV_HOVER_BG_D};
    color: #dce2eb;
}}
QPushButton#pillTab:checked {{
    background-color: {_ACCENT_MUTED};
    color: #ffffff;
    border-color: {_NAV_ACCENT_D};
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
    background-color: {_SED};
    color: #c5cdd8;
    border: 1px solid {_BC_D_S};
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
    background-color: {_SCD};
    border: 1px solid {_BC_D};
    border-radius: 14px;
}}
QFrame#cardWarning {{
    background-color: {_SCD};
    border: 1px solid #c4a035;
    border-radius: 14px;
}}
QFrame#loginCard {{
    background-color: {_SCD};
    border: 1px solid {_BC_D};
    border-radius: 12px;
}}
QFrame#loginFormSeparator {{
    background-color: {_BC_D};
    border: none;
    margin-top: 4px;
    margin-bottom: 4px;
}}
QLabel#loginTitle {{
    font-size: 14px;
    font-weight: 600;
    color: #e8eaef;
    letter-spacing: -0.02em;
    margin-bottom: 0px;
}}
QLabel#loginFieldLabel {{
    font-size: 11px;
    font-weight: 500;
    color: #8b95a8;
    margin-top: 2px;
}}
QLabel#loginFooter {{
    font-size: 11px;
    line-height: 1.45;
    color: #8b95a8;
    padding: 14px 16px 10px 16px;
    margin-top: 12px;
    margin-bottom: 4px;
    border-top: 1px solid {_BC_D};
}}
QFrame#loginCard QLineEdit,
QFrame#loginCard QComboBox {{
    padding: 6px 10px;
    min-height: 16px;
    font-size: 13px;
    border-radius: 8px;
}}
QFrame#loginCard QPushButton#primary {{
    padding: 8px 12px;
    min-height: 16px;
    font-size: 13px;
    border-radius: 8px;
    margin-top: 2px;
}}
QFrame#loginCard QPushButton#ghost {{
    padding: 6px 12px;
    min-height: 16px;
    font-size: 12px;
    border-radius: 8px;
}}

/* ---- Buttons ---- */
QPushButton {{
    background-color: {_SCD};
    color: #e8eaef;
    border: 1px solid {_BC_D_S};
    border-radius: 10px;
    padding: 10px 18px;
    min-height: 22px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {_SED};
    border-color: {_BC_D_S};
}}
QPushButton:pressed {{
    background-color: {_SBD};
}}
QPushButton:disabled {{
    color: #5c6570;
    border-color: {_SED};
}}

QPushButton#primary {{
    background-color: {_ACCENT};
    color: #ffffff;
    border: 1px solid {_ACCENT_HOVER};
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background-color: {_ACCENT_HOVER};
    border-color: {_ACCENT_HOVER};
}}
QPushButton#primary:pressed {{
    background-color: {_ACCENT_MUTED};
}}

QPushButton#ghost {{
    background-color: transparent;
    color: #b4bcc8;
    border: 1px solid {_BC_D_S};
}}
QPushButton#ghost:hover {{
    background-color: {_NAV_HOVER_BG_D};
    color: #e8eaef;
    border-color: {_BC_D_S};
}}

QPushButton#qtyAdjBtn {{
    background-color: {_SED};
    color: #e8eaef;
    border: 1px solid {_BC_D_S};
    border-radius: 6px;
    font-size: 16px;
    font-weight: 700;
    padding: 0;
}}
QPushButton#qtyAdjBtn:hover {{
    background-color: {_NAV_HOVER_BG_D};
    border-color: {_ACCENT};
    color: {_ACCENT_HOVER};
}}
QPushButton#qtyAdjBtn:pressed {{
    background-color: {_SCD};
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
    background-color: {_SUCCESS};
    color: #ecfdf5;
    border: 1px solid {_SUCCESS_HOVER};
    font-weight: 600;
}}
QPushButton#success:hover {{
    background-color: {_SUCCESS_HOVER};
    border-color: {_SUCCESS_HOVER};
    color: #052e16;
}}

/* ---- Inputs ---- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {_SED};
    border: 1px solid {_BC_D_S};
    border-radius: 10px;
    padding: 9px 12px;
    min-height: 22px;
    color: #e8eaef;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {_ACCENT};
    background-color: {_SCD};
}}
QComboBox::drop-down {{
    border: none;
    width: 32px;
}}
QComboBox QAbstractItemView {{
    background-color: {_SCD};
    selection-background-color: {_SED};
    border: 1px solid {_BC_D_S};
    border-radius: 8px;
    padding: 4px;
}}

/* POS cart qty: global QDoubleSpinBox padding clips numbers in short rows */
QWidget#cartQtyCell {{
    background-color: transparent;
}}
QDoubleSpinBox#cartQtySpin {{
    padding: 0px 2px;
    min-height: 24px;
    max-height: 28px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    color: #f1f5f9;
    background-color: {_SCD};
    border: 1px solid {_BC_D_S};
}}
QDoubleSpinBox#cartQtySpin:focus {{
    border: 1px solid {_ACCENT};
    background-color: #0c1520;
}}
QDoubleSpinBox#cartQtySpin QLineEdit {{
    padding: 0px 1px;
    margin: 0px;
    min-height: 20px;
    background-color: transparent;
    color: #f1f5f9;
    border: none;
    font-weight: 600;
    font-size: 12px;
}}
QWidget#cartQtyCell QPushButton#qtyAdjBtn {{
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
    font-size: 15px;
    padding: 0;
}}

/* ---- Tables ---- */
QTableWidget, QTableView {{
    background-color: {_SED};
    alternate-background-color: {_SCD};
    gridline-color: {_BC_D};
    border: 1px solid {_BC_D};
    border-radius: 14px;
}}
QTableWidget::item, QTableView::item {{
    padding: 8px;
    border: none;
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: #1a3040;
    color: #f0f4f8;
}}
QTableWidget::item:hover:!selected, QTableView::item:hover:!selected {{
    background-color: {_NAV_HOVER_BG_D};
}}
QHeaderView::section {{
    background-color: {_SCD};
    color: #b4bcc8;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid {_BC_D};
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}

QWidget#dashboardInner {{
    background-color: transparent;
}}

QTabWidget::pane {{
    border: 1px solid {_BC_D};
    border-radius: 10px;
    background-color: {_SCD};
    top: -1px;
    padding: 8px;
}}
QTabBar::tab {{
    background-color: {_SED};
    color: {_NAV_MUTED_FG_D};
    border: 1px solid {_BC_D};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 16px;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    background-color: {_SCD};
    color: #f8fafc;
    font-weight: 600;
    border-bottom: 2px solid {_NAV_ACCENT_D};
    margin-bottom: -1px;
}}
QTabBar::tab:hover:!selected {{
    background-color: {_NAV_HOVER_BG_D};
    color: #f1f5f9;
}}

QTreeWidget {{
    background-color: {_SED};
    alternate-background-color: {_SCD};
    border: 1px solid {_BC_D};
    border-radius: 10px;
}}
QTreeWidget::item {{
    padding: 6px 4px;
}}
QTreeWidget::item:selected {{
    background-color: #1a3040;
    color: #f0f4f8;
}}
QTreeWidget::item:hover:!selected {{
    background-color: {_NAV_HOVER_BG_D};
}}

/* ---- Scrollbars ---- */
QScrollBar:vertical {{
    background: {_SED};
    width: 10px;
    margin: 4px 2px 4px 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {_BC_D_S};
    min-height: 36px;
    border-radius: 5px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {_BC_D_S};
}}
QScrollBar:horizontal {{
    background: {_SED};
    height: 10px;
    margin: 0 4px 2px 4px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {_BC_D_S};
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
    border: 2px solid {_BC_D_S};
    background-color: {_SED};
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
    background-color: {_SBD};
}}
QTextEdit, QPlainTextEdit {{
    background-color: {_SED};
    border: 1px solid {_BC_D_S};
    border-radius: 10px;
    padding: 10px;
    color: #e8eaef;
}}

QDialogButtonBox QPushButton {{
    min-width: 88px;
}}

/* Shop logo drop target */
QLabel#shopLogo[logoState="image"] {{
    border: 2px solid {_BC_D_S};
    border-radius: 999px;
    background-color: {_SCD};
}}
QLabel#shopLogo[logoState="empty"] {{
    border: 2px dashed {_BC_D_S};
    border-radius: 999px;
    color: #8b95a8;
    font-weight: 700;
    background-color: {_SED};
}}
"""

_LIGHT_QSS = f"""
QMainWindow, QWidget {{
    background-color: {_SBL};
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
    background-color: {_SCL};
    color: #1a1f28;
    border: 1px solid {_BC_L};
    border-radius: 8px;
    padding: 8px 10px;
}}

QMenu {{
    background-color: {_SCL};
    border: 1px solid {_BC_L};
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
    background-color: {_SCL};
    border: 1px solid {_BC_L};
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
    color: {_NAV_MUTED_FG_L};
}}
QListWidget::item:selected {{
    background-color: {_SEL};
    color: #0f172a;
    border-left: 3px solid {_NAV_ACCENT_L};
    font-weight: 600;
}}
QListWidget::item:hover:!selected {{
    background-color: {_NAV_HOVER_BG_L};
    color: #1e293b;
}}

QFrame#topBar {{
    background-color: {_SCL};
    border: none;
    border-bottom: 1px solid {_BC_L};
}}
QFrame#topBar QLabel {{
    color: #4a5568;
    font-size: 13px;
}}

QFrame#appFooter {{
    background-color: {_SBL};
    border-top: 1px solid {_BC_L};
}}
QLabel#appFooterText {{
    color: #6b7280;
    font-size: 11px;
}}

QWidget#contentHost {{
    background-color: {_SBL};
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
    background-color: {_SCL};
    border: 1px solid #c5cdd8;
    border-radius: 12px;
    padding: 10px 14px;
    min-height: 20px;
}}
QPushButton#iconButton {{
    background-color: {_SCL};
    border: 1px solid {_BC_L};
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
    background-color: {_SEL};
    border: 1px solid {_BC_L};
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
QWidget#dashboardSalesChart {{
    background-color: transparent;
    min-height: 260px;
}}
QLabel#chartPlaceholderTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {_ACCENT_MUTED};
    letter-spacing: 0.02em;
}}
QFrame#donutPlaceholder {{
    background-color: {_SCL};
    border: 3px solid {_ACCENT};
    border-radius: 60px;
}}
QLabel#donutValue {{
    font-size: 22px;
    font-weight: 700;
    color: #111827;
}}
QLabel#dashboardActionBadge {{
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748b;
    background-color: transparent;
}}
QLabel#dashboardActionName {{
    font-size: 11px;
    font-weight: 600;
    color: #0f172a;
    background-color: transparent;
}}
QFrame#dashboardActionTileExpiring {{
    background-color: {_SCL};
    border: 1px solid #fde68a;
    border-radius: 12px;
    border-left: 4px solid #d97706;
}}
QFrame#dashboardActionTileLow {{
    background-color: {_SCL};
    border: 1px solid {_BC_L};
    border-radius: 12px;
    border-left: 4px solid {_ACCENT};
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
    background-color: #ecfeff;
    color: #0e7490;
    border-color: {_NAV_ACCENT_L};
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
    border: 1px solid {_BC_L};
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
    background-color: {_SCL};
    border: 1px solid {_BC_L};
    border-radius: 14px;
}}
QFrame#cardWarning {{
    background-color: #fffbeb;
    border: 1px solid #f59e0b;
    border-radius: 14px;
}}
QFrame#loginCard {{
    background-color: {_SCL};
    border: 1px solid {_BC_L};
    border-radius: 12px;
}}
QFrame#loginFormSeparator {{
    background-color: {_BC_L};
    border: none;
    margin-top: 4px;
    margin-bottom: 4px;
}}
QLabel#loginTitle {{
    font-size: 14px;
    font-weight: 600;
    color: #111827;
    letter-spacing: -0.02em;
    margin-bottom: 0px;
}}
QLabel#loginFieldLabel {{
    font-size: 11px;
    font-weight: 500;
    color: #6b7280;
    margin-top: 2px;
}}
QLabel#loginFooter {{
    font-size: 11px;
    line-height: 1.45;
    color: #6b7280;
    padding: 14px 16px 10px 16px;
    margin-top: 12px;
    margin-bottom: 4px;
    border-top: 1px solid #e5e7eb;
}}
QFrame#loginCard QLineEdit,
QFrame#loginCard QComboBox {{
    padding: 6px 10px;
    min-height: 16px;
    font-size: 13px;
    border-radius: 8px;
}}
QFrame#loginCard QPushButton#primary {{
    padding: 8px 12px;
    min-height: 16px;
    font-size: 13px;
    border-radius: 8px;
    margin-top: 2px;
}}
QFrame#loginCard QPushButton#ghost {{
    padding: 6px 12px;
    min-height: 16px;
    font-size: 12px;
    border-radius: 8px;
}}

QPushButton {{
    background-color: {_SCL};
    color: #1a1f28;
    border: 1px solid #c5cdd8;
    border-radius: 10px;
    padding: 10px 18px;
    min-height: 22px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {_NAV_HOVER_BG_L};
    border-color: {_BC_L_S};
}}
QPushButton:pressed {{
    background-color: {_SEL};
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
    background-color: {_ACCENT_MUTED};
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

QPushButton#qtyAdjBtn {{
    background-color: #f8fafc;
    color: #0f172a;
    border: 1px solid {_BC_L};
    border-radius: 6px;
    font-size: 16px;
    font-weight: 700;
    padding: 0;
}}
QPushButton#qtyAdjBtn:hover {{
    background-color: #ecfeff;
    border-color: {_ACCENT};
    color: {_ACCENT_MUTED};
}}
QPushButton#qtyAdjBtn:pressed {{
    background-color: #e0f2fe;
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
    background-color: {_SUCCESS};
    color: #ffffff;
    border: 1px solid {_SUCCESS};
    font-weight: 600;
}}
QPushButton#success:hover {{
    background-color: {_SUCCESS_HOVER};
    border-color: {_SUCCESS_HOVER};
    color: #052e16;
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {_SCL};
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
    background-color: {_SCL};
    selection-background-color: #e8f4f8;
    border: 1px solid {_BC_L};
    border-radius: 8px;
    padding: 4px;
}}

QWidget#cartQtyCell {{
    background-color: transparent;
}}
QDoubleSpinBox#cartQtySpin {{
    padding: 0px 2px;
    min-height: 24px;
    max-height: 28px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    color: #0f172a;
    background-color: #ffffff;
    border: 1px solid {_BC_L};
}}
QDoubleSpinBox#cartQtySpin:focus {{
    border: 1px solid {_ACCENT};
    background-color: #ffffff;
}}
QDoubleSpinBox#cartQtySpin QLineEdit {{
    padding: 0px 1px;
    margin: 0px;
    min-height: 20px;
    background-color: transparent;
    color: #0f172a;
    border: none;
    font-weight: 600;
    font-size: 12px;
}}
QWidget#cartQtyCell QPushButton#qtyAdjBtn {{
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
    font-size: 15px;
    padding: 0;
}}

QTableWidget, QTableView {{
    background-color: {_SEL};
    alternate-background-color: {_SCL};
    gridline-color: {_BC_L};
    border: 1px solid {_BC_L};
    border-radius: 14px;
}}
QTableWidget::item, QTableView::item {{
    padding: 8px;
    border: none;
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: #cffafe;
    color: #0e7490;
}}
QTableWidget::item:hover:!selected, QTableView::item:hover:!selected {{
    background-color: {_NAV_HOVER_BG_L};
}}
QHeaderView::section {{
    background-color: {_SEL};
    color: #4b5563;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid {_BC_L};
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}

QWidget#dashboardInner {{
    background-color: transparent;
}}

QTabWidget::pane {{
    border: 1px solid {_BC_L};
    border-radius: 10px;
    background-color: {_SCL};
    top: -1px;
    padding: 8px;
}}
QTabBar::tab {{
    background-color: {_SEL};
    color: {_NAV_MUTED_FG_L};
    border: 1px solid {_BC_L};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 16px;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    background-color: {_SCL};
    color: #0f172a;
    font-weight: 600;
    border-bottom: 2px solid {_NAV_ACCENT_L};
    margin-bottom: -1px;
}}
QTabBar::tab:hover:!selected {{
    background-color: {_NAV_HOVER_BG_L};
    color: #1e293b;
}}

QTreeWidget {{
    background-color: {_SEL};
    alternate-background-color: {_SCL};
    border: 1px solid {_BC_L};
    border-radius: 10px;
}}
QTreeWidget::item {{
    padding: 6px 4px;
}}
QTreeWidget::item:selected {{
    background-color: #cffafe;
    color: #0e7490;
}}
QTreeWidget::item:hover:!selected {{
    background-color: {_NAV_HOVER_BG_L};
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
    background-color: {_SCL};
}}
QRadioButton::indicator {{
    border-radius: 9px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {_ACCENT};
    border-color: {_ACCENT};
}}

QDialog {{
    background-color: {_SBL};
}}
QTextEdit, QPlainTextEdit {{
    background-color: {_SCL};
    border: 1px solid #c5cdd8;
    border-radius: 10px;
    padding: 10px;
    color: #1a1f28;
}}

QDialogButtonBox QPushButton {{
    min-width: 88px;
}}

QLabel#shopLogo[logoState="image"] {{
    border: 2px solid {_BC_L};
    border-radius: 999px;
    background-color: {_SCL};
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
