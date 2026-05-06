"""qt_styles.py — GamMarket POS global Qt stylesheets (dark + light).

Single source of truth for all QSS applied to the Qt shell.
Palette is 100 % aligned with theme_tokens.py teal ramp.

Colour roles
────────────
_ACCENT        → TEAL_600  #167A6A  primary button fill
_ACCENT_HOVER  → TEAL_500  #1A9680  button hover
_ACCENT_MUTED  → TEAL_700  #155652  deeper teal / muted primary
_SUCCESS       → TEAL_400  #1DB39E  success / accent border
_SUCCESS_HOVER → TEAL_500  #1A9680

Dark surfaces   → deep teal-dark (#0A1F1D → #132E2B → #1E4540)
Light surfaces  → warm grey-white (#F0F4F3 → #FFFFFF → #E2E8E6)
"""

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

_ACCENT        = TOKENS.PRIMARY          # #167A6A
_ACCENT_HOVER  = TOKENS.PRIMARY_HOVER    # #1A9680
_ACCENT_MUTED  = TOKENS.PRIMARY_MUTED   # #155652
_SUCCESS       = TOKENS.SUCCESS          # #1DB39E
_SUCCESS_HOVER = TOKENS.SUCCESS_HOVER    # #1A9680

_SBD = SURFACE_BASE_DARK       # #0A1F1D
_SCD = SURFACE_CARD_DARK       # #132E2B
_SED = SURFACE_ELEVATED_DARK   # #1E4540
_SBL = SURFACE_BASE_LIGHT      # #F0F4F3
_SCL = SURFACE_CARD_LIGHT      # #FFFFFF
_SEL = SURFACE_ELEVATED_LIGHT  # #E2E8E6

_BC_D    = CTK_CARD_BORDER[1]        # #1E4540
_BC_D_S  = CTK_CARD_BORDER_STRONG[1] # #1E4540
_BC_L    = CTK_CARD_BORDER[0]        # #E2E8E6
_BC_L_S  = CTK_CARD_BORDER_STRONG[0] # #C8D4D2

_NAV_MUTED_FG_D = CTK_NAV_TEXT_MUTED[1]    # #94A3B8
_NAV_HOVER_BG_D = CTK_NAV_HOVER_SURFACE[1] # #132E2B
_NAV_ACCENT_D   = CTK_NAV_BORDER_ACCENT[1] # #1DB39E

_NAV_MUTED_FG_L = CTK_NAV_TEXT_MUTED[0]    # #6B7280
_NAV_HOVER_BG_L = CTK_NAV_HOVER_SURFACE[0] # #EEF7F5
_NAV_ACCENT_L   = CTK_NAV_BORDER_ACCENT[0] # #1DB39E

# Brand teal literals used inside login panel (scoped QSS)
_T_LOGIN       = "#167A6A"   # primary login button
_T_LOGIN_HOVER = "#155652"   # login button hover
_T_LOGIN_RING  = "#1DB39E"   # focus ring / accent
_T_LOGIN_LIGHT = "#EEF7F5"   # secure strip fill

_DARK_QSS = f"""
/* ═══════════════════════════════════════════════════
   BASE
═══════════════════════════════════════════════════ */
QMainWindow, QWidget {{
    background-color: {_SBD};
    color: #F0F4F3;
    font-family: "Inter", "Segoe UI", "SF Pro Text", system-ui, sans-serif;
    font-size: 14px;
    selection-background-color: {_ACCENT};
    selection-color: #ffffff;
}}

QFrame, QGroupBox, QStackedWidget, QTabWidget, QScrollArea, QListView, QTreeView,
QTableView, QTableWidget, QTextEdit, QPlainTextEdit, QLineEdit, QComboBox,
QSpinBox, QDoubleSpinBox, QPushButton, QToolButton, QDateEdit, QDateTimeEdit,
QTimeEdit, QAbstractSpinBox, QAbstractItemView {{
    background-clip: padding;
    outline: none;
}}

QGroupBox {{
    border: 1px solid {_BC_D};
    border-radius: 12px;
    margin-top: 10px;
    padding: 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #94A3B8;
    font-weight: 600;
}}

QSplitter::handle           {{ background-color: {_BC_D}; }}
QSplitter::handle:horizontal {{ width: 2px; }}
QSplitter::handle:vertical   {{ height: 2px; }}

QLabel {{ background-color: transparent; }}

QToolTip {{
    background-color: {_SCD};
    color: #F0F4F3;
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
QMenu::item:selected {{ background-color: {_SED}; }}

QScrollArea, QAbstractScrollArea {{
    border: none;
    background-color: transparent;
}}
QScrollArea > QWidget > QWidget {{ background-color: transparent; }}

/* ═══════════════════════════════════════════════════
   SHELL — sidebar
═══════════════════════════════════════════════════ */
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
    color: #F0F4F3;
    border-left: 3px solid {_NAV_ACCENT_D};
    font-weight: 600;
}}
QListWidget::item:hover:!selected {{
    background-color: {_NAV_HOVER_BG_D};
    color: #C8D4D2;
}}

/* ═══════════════════════════════════════════════════
   SHELL — top bar / footer
═══════════════════════════════════════════════════ */
QFrame#topBar {{
    background-color: {_SCD};
    border: none;
    border-bottom: 1px solid {_BC_D};
}}
QFrame#topBar QLabel {{
    color: #94A3B8;
    font-size: 13px;
}}

QFrame#appFooter {{
    background-color: {_SBD};
    border-top: 1px solid {_BC_D};
}}
QLabel#appFooterText {{
    color: #6B7280;
    font-size: 11px;
}}

QWidget#contentHost {{ background-color: {_SBD}; }}

/* ═══════════════════════════════════════════════════
   TYPOGRAPHY
═══════════════════════════════════════════════════ */
QLabel#pageTitle {{
    font-size: 22px;
    font-weight: 700;
    color: #F0F4F3;
    letter-spacing: -0.4px;
}}
QLabel#pageSubtitle {{
    font-size: 14px;
    color: #94A3B8;
}}
QLabel#sidebarBrandName {{
    font-size: 15px;
    font-weight: 700;
    color: #F0F4F3;
}}
QLabel#sidebarBrandTag {{
    font-size: 11px;
    color: #94A3B8;
}}
QLabel#topBarUser {{
    color: #94A3B8;
    font-size: 13px;
    max-width: 220px;
}}
QLabel#userAvatar {{
    background-color: {_ACCENT_MUTED};
    color: #EEF7F5;
    border-radius: 21px;
    font-weight: 700;
    font-size: 15px;
    border: 2px solid {_BC_D_S};
}}
QLabel#title {{
    font-size: 24px;
    font-weight: 700;
    color: #F0F4F3;
    letter-spacing: -0.3px;
}}
QLabel#section {{
    font-size: 14px;
    font-weight: 600;
    color: #C8D4D2;
}}
QLabel#muted {{
    color: #94A3B8;
    font-size: 14px;
}}
QLabel#kpiValue {{
    font-size: 22px;
    font-weight: 700;
    color: #F0F4F3;
    letter-spacing: -0.5px;
}}
QLabel#kpiValueSm {{
    font-size: 16px;
    font-weight: 700;
    color: #E2E8E6;
}}
QLabel#errorText {{
    color: #FCA5A5;
    font-size: 12px;
}}
QLabel#statusOk {{
    color: {_SUCCESS};
    font-weight: 600;
}}
QLabel#statusBad {{
    color: #EF4444;
    font-weight: 600;
}}
QLabel#heroTime {{
    font-size: 22px;
    font-weight: 700;
    color: {_SUCCESS};
    letter-spacing: -0.3px;
}}
QLabel#pillNeutral {{
    background-color: {_SED};
    color: #94A3B8;
    border: 1px solid {_BC_D_S};
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}

/* ═══════════════════════════════════════════════════
   SEARCH / ICON BUTTONS
═══════════════════════════════════════════════════ */
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
QPushButton#iconButton:hover {{ background-color: {_SED}; }}

QListWidget#sidebarNav {{ background-color: transparent; }}

/* ═══════════════════════════════════════════════════
   DASHBOARD
═══════════════════════════════════════════════════ */
QLabel#heroMetric {{
    font-size: 36px;
    font-weight: 700;
    color: #F0F4F3;
    letter-spacing: -1px;
}}
QFrame#miniKpiCard {{
    background-color: {_SED};
    border: 1px solid {_BC_D};
    border-radius: 14px;
}}
QLabel#miniKpiTitle {{
    font-size: 12px;
    color: #94A3B8;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
QLabel#miniKpiValue {{
    font-size: 20px;
    font-weight: 700;
    color: #F0F4F3;
}}
QWidget#dashboardSalesChart {{
    background-color: transparent;
    min-height: 260px;
}}
QLabel#chartPlaceholderTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {_SUCCESS};
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
    color: #F0F4F3;
}}
QLabel#dashboardActionBadge {{
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94A3B8;
    background-color: transparent;
}}
QLabel#dashboardActionName {{
    font-size: 11px;
    font-weight: 600;
    color: #E2E8E6;
    background-color: transparent;
}}
QFrame#dashboardActionTileExpiring {{
    background-color: {_SCD};
    border: 1px solid #92400E;
    border-radius: 12px;
    border-left: 4px solid #F59E0B;
}}
QFrame#dashboardActionTileLow {{
    background-color: {_SCD};
    border: 1px solid {_BC_D};
    border-radius: 12px;
    border-left: 4px solid {_ACCENT};
}}
QPushButton#pillTab {{
    background-color: transparent;
    color: #6B7280;
    border: 1px solid {_BC_D_S};
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#pillTab:hover {{
    background-color: {_NAV_HOVER_BG_D};
    color: #C8D4D2;
}}
QPushButton#pillTab:checked {{
    background-color: {_ACCENT_MUTED};
    color: #EEF7F5;
    border-color: {_NAV_ACCENT_D};
}}
QWidget#dashboardInner {{ background-color: transparent; }}

/* ═══════════════════════════════════════════════════
   POS
═══════════════════════════════════════════════════ */
QFrame#posTotalCard {{
    background-color: {_SED};
    border: 1px solid {_ACCENT};
    border-radius: 12px;
}}
QLabel#posTotalValue {{
    font-size: 30px;
    font-weight: 800;
    color: #F0F4F3;
    letter-spacing: -0.4px;
}}
QWidget#cartQtyCell {{ background-color: transparent; }}
QDoubleSpinBox#cartQtySpin {{
    padding: 0px 2px;
    min-height: 24px;
    max-height: 28px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    color: #E2E8E6;
    background-color: {_SCD};
    border: 1px solid {_BC_D_S};
}}
QDoubleSpinBox#cartQtySpin:focus {{
    border: 1px solid {_ACCENT};
    background-color: {_SBD};
}}
QDoubleSpinBox#cartQtySpin QLineEdit {{
    padding: 0px 1px;
    margin: 0px;
    min-height: 20px;
    background-color: transparent;
    color: #E2E8E6;
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

/* ═══════════════════════════════════════════════════
   CARDS
═══════════════════════════════════════════════════ */
QFrame#card {{
    background-color: {_SCD};
    border: 1px solid {_BC_D};
    border-radius: 16px;
}}
QFrame#cardWarning {{
    background-color: {_SCD};
    border: 1px solid #F59E0B;
    border-radius: 14px;
}}

/* ═══════════════════════════════════════════════════
   LOGIN — shared dark overrides
═══════════════════════════════════════════════════ */
QFrame#loginCard {{
    background-color: {_SCD};
    border: 1px solid {_BC_D};
    border-radius: 12px;
}}
QFrame#loginProfileCard {{
    background-color: {_SCD};
    border: 1px solid {_BC_D};
    border-radius: 12px;
}}
QFrame#loginProfileCard QLineEdit,
QFrame#loginProfileCard QComboBox {{
    padding: 10px 12px;
    min-height: 22px;
    font-size: 14px;
    border-radius: 8px;
}}
QFrame#loginProfileCard QPushButton#ghost {{
    padding: 6px 12px;
    min-height: 16px;
    font-size: 12px;
    border-radius: 8px;
}}
QFrame#loginFormSeparator {{
    background-color: {_BC_D};
    border: none;
    margin-top: 4px;
    margin-bottom: 4px;
}}
QLabel#loginTitle {{
    font-size: 20px;
    font-weight: 700;
    color: #F0F4F3;
    letter-spacing: -0.02em;
    margin-bottom: 2px;
}}
QLabel#loginFieldLabel {{
    font-size: 12px;
    font-weight: 500;
    color: #94A3B8;
    margin-top: 4px;
}}
QLabel#loginFooter {{
    font-size: 12px;
    line-height: 1.45;
    color: #94A3B8;
    padding: 12px 16px 8px 16px;
    margin-top: 12px;
    margin-bottom: 4px;
    border-top: 1px solid {_BC_D};
}}
QFrame#loginCard QLineEdit,
QFrame#loginCard QComboBox {{
    padding: 10px 12px;
    min-height: 22px;
    font-size: 14px;
    border-radius: 8px;
}}
QFrame#loginCard QPushButton#primary {{
    padding: 10px 12px;
    min-height: 24px;
    font-size: 14px;
    border-radius: 10px;
    margin-top: 6px;
}}
QFrame#loginCard QPushButton#ghost {{
    padding: 6px 12px;
    min-height: 16px;
    font-size: 12px;
    border-radius: 8px;
}}

/* LOGIN — split panel (scoped so brand left stays dark-teal) */
QWidget#loginShell              {{ background-color: #F0F4F3; }}
QFrame#loginLeftPanel           {{ border: none; background-color: {_T_LOGIN}; }}
QFrame#loginLeftOverlay         {{ background-color: rgba(0,0,0,0.42); border: none; }}
QLabel#loginBrandTitle          {{ color: #ffffff; font-size: 32px; font-weight: 800; letter-spacing: -0.03em; }}
QLabel#loginBrandTagline        {{ color: rgba(255,255,255,0.80); font-size: 14px; line-height: 1.5; }}
QFrame#loginRightPanel          {{ background-color: #F0F4F3; border: none; }}

QWidget#loginBrandFeature,
QWidget#loginBrandFeatureCol    {{ background-color: transparent; border: none; }}

QFrame#loginShopToolbar {{
    background-color: #ffffff;
    border: 1px solid #E2E8E6;
    border-radius: 10px;
}}
QFrame#loginShopToolbar QComboBox {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 8px 10px;
    min-height: 28px;
    font-size: 14px;
    color: #111827;
}}
QFrame#loginShopToolbar QComboBox:focus   {{ border: 1px solid {_T_LOGIN_RING}; }}
QFrame#loginShopToolbar QComboBox:hover   {{ background-color: #F5FBF9; }}
QFrame#loginShopToolbar QPushButton#ghost {{
    background-color: transparent;
    border: none;
    color: {_T_LOGIN};
    font-weight: 600;
    padding: 8px 12px;
}}
QFrame#loginShopToolbar QPushButton#ghost:hover {{
    background-color: rgba(22,122,106,0.08);
    color: {_T_LOGIN_HOVER};
}}

QFrame#loginRightPanel QFrame#loginOuterCard,
QFrame#loginRightPanel QFrame#loginCard,
QFrame#loginRightPanel QFrame#loginProfileCard {{
    background-color: #ffffff;
    border: none;
    border-radius: 16px;
}}
QFrame#loginRightPanel QFrame#loginOuterCard > QWidget#loginShopBlock,
QFrame#loginRightPanel QFrame#loginOuterCard > QStackedWidget#loginMainStack {{
    background-color: transparent;
}}
QFrame#loginRightPanel QFrame#loginOuterCard QStackedWidget#loginMainStack > QScrollArea#loginSigninScroll,
QFrame#loginRightPanel QFrame#loginOuterCard QStackedWidget#loginMainStack > QScrollArea#loginSignupScroll {{
    background-color: transparent;
    border: none;
}}
QFrame#loginRightPanel QFrame#loginOuterCard QScrollArea > QWidget > QWidget          {{ background-color: transparent; }}
QFrame#loginRightPanel QFrame#loginOuterCard QWidget#loginSigninPage QWidget,
QFrame#loginRightPanel QFrame#loginOuterCard QWidget#loginSignupPage QWidget          {{ background-color: transparent; }}
QFrame#loginRightPanel QFrame#loginOuterCard QFrame#loginProfileCard {{
    background-color: #ffffff;
    border: none;
    border-radius: 16px;
}}
QFrame#loginRightPanel QFrame#loginOuterCard QLabel                                    {{ color: #475569; }}
QFrame#loginRightPanel QFrame#loginOuterCard QLabel#loginWelcomeHead                   {{ color: #111827; font-size: 26px; font-weight: 800; letter-spacing: -0.03em; }}
QFrame#loginRightPanel QLabel#loginTitle                                               {{ color: #111827; font-size: 24px; font-weight: 700; letter-spacing: -0.02em; }}
QFrame#loginRightPanel QFrame#loginOuterCard QLabel#loginFieldLabel,
QFrame#loginRightPanel QFrame#loginCard QLabel#loginFieldLabel,
QFrame#loginRightPanel QFrame#loginProfileCard QLabel#loginFieldLabel                  {{ color: #64748B; font-size: 12px; font-weight: 500; }}
QFrame#loginRightPanel QFrame#loginOuterCard QLabel#muted,
QFrame#loginRightPanel QFrame#loginCard QLabel#muted,
QFrame#loginRightPanel QFrame#loginProfileCard QLabel#muted                            {{ color: #64748B; font-size: 14px; }}

QFrame#loginRightPanel QFrame#loginOuterCard QLineEdit,
QFrame#loginRightPanel QFrame#loginCard QLineEdit,
QFrame#loginRightPanel QFrame#loginProfileCard QLineEdit {{
    background-color: #ffffff;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 9px 11px;
    min-height: 36px;
    font-size: 14px;
    color: #111827;
}}
QFrame#loginRightPanel QFrame#loginOuterCard QLineEdit:focus,
QFrame#loginRightPanel QFrame#loginCard QLineEdit:focus,
QFrame#loginRightPanel QFrame#loginProfileCard QLineEdit:focus    {{ border: 2px solid {_T_LOGIN_RING}; }}

QFrame#loginRightPanel QFrame#loginOuterCard QPushButton#primary,
QFrame#loginRightPanel QFrame#loginCard QPushButton#primary,
QFrame#loginRightPanel QFrame#loginProfileCard QPushButton#primary {{
    background-color: {_T_LOGIN};
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 11px 16px;
    min-height: 40px;
    margin-top: 8px;
    font-weight: 700;
    font-size: 14px;
}}
QFrame#loginRightPanel QFrame#loginOuterCard QPushButton#primary:hover,
QFrame#loginRightPanel QFrame#loginCard QPushButton#primary:hover,
QFrame#loginRightPanel QFrame#loginProfileCard QPushButton#primary:hover  {{ background-color: {_T_LOGIN_HOVER}; }}

QFrame#loginRightPanel QFrame#loginOuterCard QPushButton#ghost,
QFrame#loginRightPanel QFrame#loginCard QPushButton#ghost,
QFrame#loginRightPanel QFrame#loginProfileCard QPushButton#ghost {{
    background-color: transparent;
    border: none;
    color: {_T_LOGIN};
    border-radius: 8px;
    padding: 10px 8px;
    font-weight: 600;
}}
QFrame#loginRightPanel QFrame#loginOuterCard QPushButton#ghost:hover,
QFrame#loginRightPanel QFrame#loginCard QPushButton#ghost:hover,
QFrame#loginRightPanel QFrame#loginProfileCard QPushButton#ghost:hover {{
    background-color: rgba(22,122,106,0.07);
    color: {_T_LOGIN_HOVER};
}}

QFrame#loginRightPanel QFrame#loginFormSeparator {{
    background-color: #E2E8E6;
    border: none;
    max-height: 1px;
    margin-top: 4px;
    margin-bottom: 4px;
}}
QLabel#loginAccountLinkPrompt                    {{ color: #64748B; font-size: 13px; }}
QPushButton#loginLinkButton {{
    background: transparent;
    border: none;
    color: {_T_LOGIN};
    font-weight: 600;
    font-size: 13px;
    padding: 2px 6px;
    min-height: 0;
    qproperty-cursor: PointingHandCursor;
}}
QPushButton#loginLinkButton:hover                {{ color: {_T_LOGIN_HOVER}; }}
QFrame#loginRightPanel QLabel#loginFooter {{
    color: #64748B;
    border-top: 1px solid #E2E8E6;
    background: transparent;
    padding-top: 12px;
    margin-top: 8px;
}}
QFrame#loginRightPanel QLabel#errorText          {{ color: #DC2626; font-size: 13px; padding-top: 4px; }}
QLabel#loginLockBadge {{
    background-color: {_T_LOGIN};
    border-radius: 12px;
    min-width: 40px; min-height: 40px;
    max-width: 40px; max-height: 40px;
    padding: 8px;
    qproperty-alignment: AlignCenter;
}}
QPushButton#loginPasswordToggle {{
    background: transparent;
    border: none;
    min-width: 36px; min-height: 36px;
    padding: 0;
    border-radius: 8px;
}}
QPushButton#loginPasswordToggle:hover     {{ background-color: rgba(22,122,106,0.08); }}
QCheckBox#loginRememberCheck {{
    color: #475569;
    font-size: 13px;
    font-weight: 500;
    spacing: 8px;
}}
QCheckBox#loginRememberCheck::indicator {{
    width: 18px; height: 18px;
    border-radius: 4px;
    border: 1px solid #CBD5E1;
    background: #ffffff;
}}
QCheckBox#loginRememberCheck::indicator:checked  {{ background-color: {_T_LOGIN}; border-color: {_T_LOGIN}; }}
QPushButton#loginForgotLink {{
    background: transparent;
    border: none;
    color: {_T_LOGIN};
    font-weight: 600;
    font-size: 13px;
    padding: 4px 8px;
    min-height: 0;
}}
QPushButton#loginForgotLink:hover                {{ color: {_T_LOGIN_HOVER}; text-decoration: underline; }}
QPushButton#loginOutlineButton {{
    background-color: #ffffff;
    color: #111827;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
    padding: 11px 16px;
    min-height: 40px;
    font-weight: 600;
    font-size: 14px;
}}
QPushButton#loginOutlineButton:hover             {{ background-color: #F5FBF9; border-color: #94A3B8; color: #111827; }}
QWidget#loginSecureStrip {{
    background-color: {_T_LOGIN_LIGHT};
    border: 1px solid rgba(29,179,158,0.30);
    border-radius: 10px;
}}
QLabel#loginSecureBanner                         {{ color: #111827; font-size: 13px; font-weight: 500; }}
QLabel#loginOrLabel                              {{ color: #94A3B8; font-size: 12px; font-weight: 600; padding: 0 8px; }}

/* ═══════════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════════ */
QPushButton {{
    background-color: {_SCD};
    color: #E2E8E6;
    border: 1px solid {_BC_D_S};
    border-radius: 10px;
    padding: 10px 18px;
    min-height: 22px;
    font-weight: 500;
    qproperty-cursor: PointingHandCursor;
}}
QPushButton[hasIcon="true"] {{ padding-left: 14px; padding-right: 16px; }}
QPushButton:hover            {{ background-color: {_SED}; border-color: {_BC_D_S}; }}
QPushButton:pressed          {{ background-color: {_SBD}; }}
QPushButton:disabled         {{ color: #4B5563; border-color: {_SED}; }}

QPushButton#primary {{
    background-color: {_ACCENT};
    color: #ffffff;
    border: 1px solid {_ACCENT_HOVER};
    font-weight: 600;
}}
QPushButton#primary:hover   {{ background-color: {_ACCENT_HOVER}; border-color: {_ACCENT_HOVER}; }}
QPushButton#primary:pressed {{ background-color: {_ACCENT_MUTED}; }}

QPushButton#ghost {{
    background-color: transparent;
    color: #94A3B8;
    border: 1px solid {_BC_D_S};
}}
QPushButton#ghost:hover {{ background-color: {_NAV_HOVER_BG_D}; color: #E2E8E6; border-color: {_BC_D_S}; }}

QPushButton#qtyAdjBtn {{
    background-color: {_SED};
    color: #E2E8E6;
    border: 1px solid {_BC_D_S};
    border-radius: 6px;
    font-size: 16px;
    font-weight: 700;
    padding: 0;
}}
QPushButton#qtyAdjBtn:hover   {{ background-color: {_NAV_HOVER_BG_D}; border-color: {_ACCENT}; color: {_SUCCESS}; }}
QPushButton#qtyAdjBtn:pressed {{ background-color: {_SCD}; }}

QPushButton#danger {{
    background-color: #EF4444;
    color: #ffffff;
    border: 1px solid #EF4444;
}}
QPushButton#danger:hover {{ background-color: #DC2626; }}

QPushButton#success {{
    background-color: {_SUCCESS};
    color: #F0FDF4;
    border: 1px solid {_SUCCESS_HOVER};
    font-weight: 600;
}}
QPushButton#success:hover {{ background-color: {_SUCCESS_HOVER}; border-color: {_SUCCESS_HOVER}; color: #052E16; }}

/* ═══════════════════════════════════════════════════
   INPUTS
═══════════════════════════════════════════════════ */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {_SED};
    border: 1px solid {_BC_D_S};
    border-radius: 8px;
    padding: 9px 12px;
    min-height: 22px;
    color: #F0F4F3;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {_ACCENT};
    background-color: {_SCD};
}}
QComboBox::drop-down {{ border: none; width: 32px; }}
QComboBox {{ qproperty-cursor: PointingHandCursor; }}
QComboBox QAbstractItemView {{
    background-color: {_SCD};
    selection-background-color: {_SED};
    border: 1px solid {_BC_D_S};
    border-radius: 8px;
    padding: 4px;
}}

/* ═══════════════════════════════════════════════════
   TABLES
═══════════════════════════════════════════════════ */
QTableWidget, QTableView {{
    background-color: {_SED};
    alternate-background-color: {_SCD};
    gridline-color: {_BC_D};
    border: 1px solid {_BC_D};
    border-radius: 14px;
}}
QTableWidget::item, QTableView::item {{
    padding: 10px 12px;
    border: none;
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {_ACCENT_MUTED};
    color: #EEF7F5;
}}
QTableWidget::item:hover:!selected, QTableView::item:hover:!selected {{
    background-color: {_NAV_HOVER_BG_D};
}}
QHeaderView::section {{
    background-color: {_SCD};
    color: #94A3B8;
    padding: 12px 14px;
    border: none;
    border-bottom: 2px solid {_BC_D};
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}

/* ═══════════════════════════════════════════════════
   TABS / TREE
═══════════════════════════════════════════════════ */
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
    color: #F0F4F3;
    font-weight: 600;
    border-bottom: 2px solid {_NAV_ACCENT_D};
    margin-bottom: -1px;
}}
QTabBar::tab:hover:!selected {{ background-color: {_NAV_HOVER_BG_D}; color: #C8D4D2; }}

QTreeWidget {{
    background-color: {_SED};
    alternate-background-color: {_SCD};
    border: 1px solid {_BC_D};
    border-radius: 10px;
}}
QTreeWidget::item {{ padding: 6px 4px; }}
QTreeWidget::item:selected {{ background-color: {_ACCENT_MUTED}; color: #EEF7F5; }}
QTreeWidget::item:hover:!selected {{ background-color: {_NAV_HOVER_BG_D}; }}

/* ═══════════════════════════════════════════════════
   SCROLLBARS
═══════════════════════════════════════════════════ */
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
QScrollBar::handle:vertical:hover {{ background: {_ACCENT}; }}
QScrollBar:horizontal {{
    background: {_SED};
    height: 10px;
    margin: 0 4px 2px 4px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{ background: {_BC_D_S}; border-radius: 5px; margin: 2px; }}
QScrollBar::handle:horizontal:hover {{ background: {_ACCENT}; }}

/* ═══════════════════════════════════════════════════
   MISC
═══════════════════════════════════════════════════ */
QCheckBox, QRadioButton {{
    spacing: 10px;
    color: #C8D4D2;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px; height: 18px;
    border-radius: 5px;
    border: 2px solid {_BC_D_S};
    background-color: {_SED};
}}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {_ACCENT};
    border-color: {_ACCENT_HOVER};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {_ACCENT}; }}

QDialog         {{ background-color: {_SBD}; }}
QTextEdit, QPlainTextEdit {{
    background-color: {_SED};
    border: 1px solid {_BC_D_S};
    border-radius: 8px;
    padding: 10px;
    color: #F0F4F3;
}}
QDialogButtonBox QPushButton {{ min-width: 88px; }}

QLabel#shopLogo[logoState="image"] {{
    border: 2px solid {_BC_D_S};
    border-radius: 999px;
    background-color: {_SCD};
}}
QLabel#shopLogo[logoState="empty"] {{
    border: 2px dashed {_BC_D_S};
    border-radius: 999px;
    color: #6B7280;
    font-weight: 700;
    background-color: {_SED};
}}
"""

# ── LIGHT ──────────────────────────────────────────────────────────────────

_LIGHT_QSS = f"""
QMainWindow, QWidget {{
    background-color: {_SBL};
    color: #111827;
    font-family: "Inter", "Segoe UI", "SF Pro Text", system-ui, sans-serif;
    font-size: 14px;
    selection-background-color: {_ACCENT};
    selection-color: #ffffff;
}}

QLabel {{ background-color: transparent; }}

QToolTip {{
    background-color: {_SCL};
    color: #111827;
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
QMenu::item {{ padding: 10px 28px 10px 14px; border-radius: 8px; }}
QMenu::item:selected {{ background-color: {_T_LOGIN_LIGHT}; }}

QScrollArea, QAbstractScrollArea {{ border: none; background-color: transparent; }}
QScrollArea > QWidget > QWidget {{ background-color: transparent; }}

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
    background-color: {_T_LOGIN_LIGHT};
    color: {_T_LOGIN};
    border-left: 3px solid {_NAV_ACCENT_L};
    font-weight: 600;
}}
QListWidget::item:hover:!selected {{ background-color: {_NAV_HOVER_BG_L}; color: #374151; }}

QFrame#topBar {{
    background-color: {_SCL};
    border: none;
    border-bottom: 1px solid {_BC_L};
}}
QFrame#topBar QLabel {{ color: #374151; font-size: 13px; }}

QFrame#appFooter {{ background-color: {_SBL}; border-top: 1px solid {_BC_L}; }}
QLabel#appFooterText {{ color: #6B7280; font-size: 11px; }}
QWidget#contentHost {{ background-color: {_SBL}; }}

QLabel#pageTitle  {{ font-size: 22px; font-weight: 700; color: #111827; letter-spacing: -0.4px; }}
QLabel#pageSubtitle {{ font-size: 13px; color: #6B7280; }}
QLabel#sidebarBrandName {{ font-size: 15px; font-weight: 700; color: #111827; }}
QLabel#sidebarBrandTag  {{ font-size: 11px; color: #6B7280; }}
QLabel#topBarUser {{ color: #374151; font-size: 13px; max-width: 220px; }}
QLabel#userAvatar {{
    background-color: {_T_LOGIN_LIGHT};
    color: {_T_LOGIN};
    border-radius: 21px;
    font-weight: 700;
    font-size: 15px;
    border: 2px solid {_T_LOGIN_RING};
}}
QLineEdit#globalSearch {{
    background-color: {_SCL};
    border: 1px solid {_BC_L_S};
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
QPushButton#iconButton:hover {{ background-color: {_T_LOGIN_LIGHT}; }}
QListWidget#sidebarNav {{ background-color: transparent; }}

QLabel#heroMetric   {{ font-size: 36px; font-weight: 700; color: #111827; letter-spacing: -1px; }}
QFrame#miniKpiCard  {{ background-color: {_SEL}; border: 1px solid {_BC_L}; border-radius: 14px; }}
QLabel#miniKpiTitle {{ font-size: 12px; color: #6B7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
QLabel#miniKpiValue {{ font-size: 20px; font-weight: 700; color: #111827; }}
QWidget#dashboardSalesChart {{ background-color: transparent; min-height: 260px; }}
QLabel#chartPlaceholderTitle {{ font-size: 15px; font-weight: 700; color: {_ACCENT}; letter-spacing: 0.02em; }}
QFrame#donutPlaceholder {{ background-color: {_SCL}; border: 3px solid {_ACCENT}; border-radius: 60px; }}
QLabel#donutValue   {{ font-size: 22px; font-weight: 700; color: #111827; }}
QLabel#dashboardActionBadge {{ font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6B7280; background-color: transparent; }}
QLabel#dashboardActionName  {{ font-size: 11px; font-weight: 600; color: #111827; background-color: transparent; }}
QFrame#dashboardActionTileExpiring {{
    background-color: {_SCL};
    border: 1px solid #FDE68A;
    border-radius: 12px;
    border-left: 4px solid #F59E0B;
}}
QFrame#dashboardActionTileLow {{
    background-color: {_SCL};
    border: 1px solid {_BC_L};
    border-radius: 12px;
    border-left: 4px solid {_ACCENT};
}}
QPushButton#pillTab {{
    background-color: transparent;
    color: #6B7280;
    border: 1px solid {_BC_L_S};
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#pillTab:hover   {{ background-color: {_T_LOGIN_LIGHT}; color: {_T_LOGIN}; }}
QPushButton#pillTab:checked {{ background-color: {_T_LOGIN_LIGHT}; color: {_T_LOGIN}; border-color: {_T_LOGIN_RING}; font-weight: 700; }}

QLabel#title    {{ font-size: 24px; font-weight: 700; color: #111827; letter-spacing: -0.3px; }}
QLabel#section  {{ font-size: 14px; font-weight: 600; color: #374151; }}
QLabel#muted    {{ color: #6B7280; font-size: 12px; }}
QLabel#kpiValue {{ font-size: 22px; font-weight: 700; color: #111827; letter-spacing: -0.5px; }}
QLabel#kpiValueSm {{ font-size: 16px; font-weight: 700; color: #111827; }}
QFrame#posTotalCard {{ background-color: {_SEL}; border: 1px solid {_ACCENT}; border-radius: 12px; }}
QLabel#posTotalValue {{ font-size: 30px; font-weight: 800; color: #111827; letter-spacing: -0.4px; }}
QLabel#heroTime {{ font-size: 22px; font-weight: 700; color: {_ACCENT}; letter-spacing: -0.3px; }}
QLabel#pillNeutral {{
    background-color: {_T_LOGIN_LIGHT};
    color: {_T_LOGIN};
    border: 1px solid {_BC_L};
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#errorText  {{ color: #DC2626; font-size: 12px; }}
QLabel#statusOk   {{ color: {_ACCENT}; font-weight: 600; }}
QLabel#statusBad  {{ color: #DC2626; font-weight: 600; }}

QFrame#card {{ background-color: {_SCL}; border: 1px solid {_BC_L}; border-radius: 14px; }}
QFrame#cardWarning {{ background-color: #FFFBEB; border: 1px solid #F59E0B; border-radius: 14px; }}
QFrame#loginCard {{ background-color: {_SCL}; border: 1px solid {_BC_L}; border-radius: 12px; }}
QFrame#loginProfileCard {{ background-color: {_SCL}; border: 1px solid {_BC_L}; border-radius: 12px; }}
QFrame#loginProfileCard QLineEdit, QFrame#loginProfileCard QComboBox {{ padding: 10px 12px; min-height: 22px; font-size: 14px; border-radius: 8px; }}
QFrame#loginProfileCard QPushButton#ghost {{ padding: 6px 12px; min-height: 16px; font-size: 12px; border-radius: 8px; }}
QFrame#loginFormSeparator {{ background-color: {_BC_L}; border: none; margin-top: 4px; margin-bottom: 4px; }}
QLabel#loginTitle {{ font-size: 20px; font-weight: 700; color: #111827; letter-spacing: -0.02em; margin-bottom: 2px; }}
QLabel#loginFieldLabel {{ font-size: 12px; font-weight: 500; color: #6B7280; margin-top: 4px; }}
QLabel#loginFooter {{ font-size: 12px; line-height: 1.45; color: #6B7280; padding: 12px 16px 8px 16px; margin-top: 12px; margin-bottom: 4px; border-top: 1px solid {_BC_L}; }}
QFrame#loginCard QLineEdit, QFrame#loginCard QComboBox {{ padding: 10px 12px; min-height: 22px; font-size: 14px; border-radius: 8px; }}
QFrame#loginCard QPushButton#primary {{ padding: 10px 12px; min-height: 24px; font-size: 14px; border-radius: 10px; margin-top: 6px; }}
QFrame#loginCard QPushButton#ghost   {{ padding: 6px 12px; min-height: 16px; font-size: 12px; border-radius: 8px; }}

/* Light login split — same teal, white right panel */
QWidget#loginShell      {{ background-color: #F0F4F3; }}
QFrame#loginLeftPanel   {{ border: none; background-color: {_T_LOGIN}; }}
QFrame#loginLeftOverlay {{ background-color: rgba(0,0,0,0.42); border: none; }}
QLabel#loginBrandTitle  {{ color: #ffffff; font-size: 32px; font-weight: 800; letter-spacing: -0.03em; }}
QLabel#loginBrandTagline {{ color: rgba(255,255,255,0.80); font-size: 14px; line-height: 1.5; }}
QFrame#loginRightPanel  {{ background-color: #F0F4F3; border: none; }}
QWidget#loginBrandFeature, QWidget#loginBrandFeatureCol {{ background-color: transparent; border: none; }}

QFrame#loginShopToolbar {{ background-color: #ffffff; border: 1px solid {_BC_L}; border-radius: 10px; }}
QFrame#loginShopToolbar QComboBox {{ background-color: transparent; border: none; border-radius: 6px; padding: 8px 10px; min-height: 28px; font-size: 14px; color: #111827; }}
QFrame#loginShopToolbar QComboBox:focus {{ border: 1px solid {_T_LOGIN_RING}; }}
QFrame#loginShopToolbar QComboBox:hover {{ background-color: {_T_LOGIN_LIGHT}; }}
QFrame#loginShopToolbar QPushButton#ghost {{ background-color: transparent; border: none; color: {_T_LOGIN}; font-weight: 600; padding: 8px 12px; }}
QFrame#loginShopToolbar QPushButton#ghost:hover {{ background-color: rgba(22,122,106,0.08); color: {_T_LOGIN_HOVER}; }}

QFrame#loginRightPanel QFrame#loginOuterCard,
QFrame#loginRightPanel QFrame#loginCard,
QFrame#loginRightPanel QFrame#loginProfileCard {{ background-color: #ffffff; border: none; border-radius: 16px; }}
QFrame#loginRightPanel QFrame#loginOuterCard > QWidget#loginShopBlock,
QFrame#loginRightPanel QFrame#loginOuterCard > QStackedWidget#loginMainStack {{ background-color: transparent; }}
QFrame#loginRightPanel QFrame#loginOuterCard QStackedWidget#loginMainStack > QScrollArea#loginSigninScroll,
QFrame#loginRightPanel QFrame#loginOuterCard QStackedWidget#loginMainStack > QScrollArea#loginSignupScroll {{ background-color: transparent; border: none; }}
QFrame#loginRightPanel QFrame#loginOuterCard QScrollArea > QWidget > QWidget {{ background-color: transparent; }}
QFrame#loginRightPanel QFrame#loginOuterCard QWidget#loginSigninPage QWidget,
QFrame#loginRightPanel QFrame#loginOuterCard QWidget#loginSignupPage QWidget {{ background-color: transparent; }}
QFrame#loginRightPanel QFrame#loginOuterCard QFrame#loginProfileCard {{ background-color: #ffffff; border: none; border-radius: 16px; }}
QFrame#loginRightPanel QFrame#loginOuterCard QLabel {{ color: #6B7280; }}
QFrame#loginRightPanel QFrame#loginOuterCard QLabel#loginWelcomeHead {{ color: #111827; font-size: 26px; font-weight: 800; letter-spacing: -0.03em; }}
QFrame#loginRightPanel QLabel#loginTitle {{ color: #111827; font-size: 24px; font-weight: 700; letter-spacing: -0.02em; }}
QFrame#loginRightPanel QFrame#loginOuterCard QLabel#loginFieldLabel,
QFrame#loginRightPanel QFrame#loginCard QLabel#loginFieldLabel,
QFrame#loginRightPanel QFrame#loginProfileCard QLabel#loginFieldLabel {{ color: #6B7280; font-size: 12px; font-weight: 500; }}
QFrame#loginRightPanel QFrame#loginOuterCard QLabel#muted,
QFrame#loginRightPanel QFrame#loginCard QLabel#muted,
QFrame#loginRightPanel QFrame#loginProfileCard QLabel#muted {{ color: #6B7280; font-size: 14px; }}

QFrame#loginRightPanel QFrame#loginOuterCard QLineEdit,
QFrame#loginRightPanel QFrame#loginCard QLineEdit,
QFrame#loginRightPanel QFrame#loginProfileCard QLineEdit {{ background-color: #ffffff; border: 1px solid #CBD5E1; border-radius: 8px; padding: 9px 11px; min-height: 36px; font-size: 14px; color: #111827; }}
QFrame#loginRightPanel QFrame#loginOuterCard QLineEdit:focus,
QFrame#loginRightPanel QFrame#loginCard QLineEdit:focus,
QFrame#loginRightPanel QFrame#loginProfileCard QLineEdit:focus {{ border: 2px solid {_T_LOGIN_RING}; }}

QFrame#loginRightPanel QFrame#loginOuterCard QPushButton#primary,
QFrame#loginRightPanel QFrame#loginCard QPushButton#primary,
QFrame#loginRightPanel QFrame#loginProfileCard QPushButton#primary {{ background-color: {_T_LOGIN}; color: #ffffff; border: none; border-radius: 10px; padding: 11px 16px; min-height: 40px; margin-top: 8px; font-weight: 700; font-size: 14px; }}
QFrame#loginRightPanel QFrame#loginOuterCard QPushButton#primary:hover,
QFrame#loginRightPanel QFrame#loginCard QPushButton#primary:hover,
QFrame#loginRightPanel QFrame#loginProfileCard QPushButton#primary:hover {{ background-color: {_T_LOGIN_HOVER}; }}

QFrame#loginRightPanel QFrame#loginOuterCard QPushButton#ghost,
QFrame#loginRightPanel QFrame#loginCard QPushButton#ghost,
QFrame#loginRightPanel QFrame#loginProfileCard QPushButton#ghost {{ background-color: transparent; border: none; color: {_T_LOGIN}; border-radius: 8px; padding: 10px 8px; font-weight: 600; }}
QFrame#loginRightPanel QFrame#loginOuterCard QPushButton#ghost:hover,
QFrame#loginRightPanel QFrame#loginCard QPushButton#ghost:hover,
QFrame#loginRightPanel QFrame#loginProfileCard QPushButton#ghost:hover {{ background-color: rgba(22,122,106,0.07); color: {_T_LOGIN_HOVER}; }}

QFrame#loginRightPanel QFrame#loginFormSeparator {{ background-color: {_BC_L}; border: none; max-height: 1px; margin-top: 4px; margin-bottom: 4px; }}
QLabel#loginAccountLinkPrompt {{ color: #6B7280; font-size: 13px; }}
QPushButton#loginLinkButton {{ background: transparent; border: none; color: {_T_LOGIN}; font-weight: 600; font-size: 13px; padding: 2px 6px; min-height: 0; qproperty-cursor: PointingHandCursor; }}
QPushButton#loginLinkButton:hover {{ color: {_T_LOGIN_HOVER}; }}
QFrame#loginRightPanel QLabel#loginFooter {{ color: #6B7280; border-top: 1px solid {_BC_L}; background: transparent; padding-top: 12px; margin-top: 8px; }}
QFrame#loginRightPanel QLabel#errorText {{ color: #DC2626; font-size: 13px; padding-top: 4px; }}
QLabel#loginLockBadge {{ background-color: {_T_LOGIN}; border-radius: 12px; min-width: 40px; min-height: 40px; max-width: 40px; max-height: 40px; padding: 8px; qproperty-alignment: AlignCenter; }}
QPushButton#loginPasswordToggle {{ background: transparent; border: none; min-width: 36px; min-height: 36px; padding: 0; border-radius: 8px; }}
QPushButton#loginPasswordToggle:hover {{ background-color: rgba(22,122,106,0.08); }}
QCheckBox#loginRememberCheck {{ color: #374151; font-size: 13px; font-weight: 500; spacing: 8px; }}
QCheckBox#loginRememberCheck::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid #CBD5E1; background: #ffffff; }}
QCheckBox#loginRememberCheck::indicator:checked {{ background-color: {_T_LOGIN}; border-color: {_T_LOGIN}; }}
QPushButton#loginForgotLink {{ background: transparent; border: none; color: {_T_LOGIN}; font-weight: 600; font-size: 13px; padding: 4px 8px; min-height: 0; }}
QPushButton#loginForgotLink:hover {{ color: {_T_LOGIN_HOVER}; text-decoration: underline; }}
QPushButton#loginOutlineButton {{ background-color: #ffffff; color: #111827; border: 1px solid #CBD5E1; border-radius: 10px; padding: 11px 16px; min-height: 40px; font-weight: 600; font-size: 14px; }}
QPushButton#loginOutlineButton:hover {{ background-color: {_T_LOGIN_LIGHT}; border-color: #94A3B8; color: #111827; }}
QWidget#loginSecureStrip {{ background-color: {_T_LOGIN_LIGHT}; border: 1px solid rgba(29,179,158,0.30); border-radius: 10px; }}
QLabel#loginSecureBanner {{ color: #111827; font-size: 13px; font-weight: 500; }}
QLabel#loginOrLabel {{ color: #94A3B8; font-size: 12px; font-weight: 600; padding: 0 8px; }}

QPushButton {{
    background-color: {_SCL};
    color: #374151;
    border: 1px solid {_BC_L_S};
    border-radius: 10px;
    padding: 10px 18px;
    min-height: 22px;
    font-weight: 500;
}}
QPushButton[hasIcon="true"] {{ padding-left: 14px; padding-right: 16px; }}
QPushButton:hover    {{ background-color: {_NAV_HOVER_BG_L}; border-color: {_BC_L_S}; }}
QPushButton:pressed  {{ background-color: {_SEL}; }}
QPushButton:disabled {{ color: #9CA3AF; border-color: {_BC_L}; }}

QPushButton#primary {{
    background-color: {_ACCENT};
    color: #ffffff;
    border: 1px solid {_ACCENT};
    font-weight: 600;
}}
QPushButton#primary:hover   {{ background-color: {_ACCENT_HOVER}; border-color: {_ACCENT_HOVER}; }}
QPushButton#primary:pressed {{ background-color: {_ACCENT_MUTED}; }}

QPushButton#ghost {{ background-color: transparent; color: #374151; border: 1px solid {_BC_L_S}; }}
QPushButton#ghost:hover {{ background-color: {_T_LOGIN_LIGHT}; color: {_T_LOGIN}; border-color: {_T_LOGIN_RING}; }}

QPushButton#qtyAdjBtn {{
    background-color: {_SCL};
    color: #374151;
    border: 1px solid {_BC_L};
    border-radius: 6px;
    font-size: 16px;
    font-weight: 700;
    padding: 0;
}}
QPushButton#qtyAdjBtn:hover   {{ background-color: {_T_LOGIN_LIGHT}; border-color: {_ACCENT}; color: {_ACCENT}; }}
QPushButton#qtyAdjBtn:pressed {{ background-color: {_SEL}; }}

QPushButton#danger {{ background-color: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }}
QPushButton#danger:hover {{ background-color: #FEE2E2; }}

QPushButton#success {{
    background-color: {_SUCCESS};
    color: #ffffff;
    border: 1px solid {_SUCCESS};
    font-weight: 600;
}}
QPushButton#success:hover {{ background-color: {_SUCCESS_HOVER}; border-color: {_SUCCESS_HOVER}; color: #052E16; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {_SCL};
    border: 1px solid {_BC_L_S};
    border-radius: 8px;
    padding: 9px 12px;
    min-height: 22px;
    color: #111827;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {_ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 32px; }}
QComboBox QAbstractItemView {{ background-color: {_SCL}; selection-background-color: {_T_LOGIN_LIGHT}; border: 1px solid {_BC_L}; border-radius: 8px; padding: 4px; }}

QWidget#cartQtyCell {{ background-color: transparent; }}
QDoubleSpinBox#cartQtySpin {{ padding: 0px 2px; min-height: 24px; max-height: 28px; border-radius: 6px; font-size: 12px; font-weight: 600; color: #111827; background-color: #ffffff; border: 1px solid {_BC_L}; }}
QDoubleSpinBox#cartQtySpin:focus {{ border: 1px solid {_ACCENT}; background-color: #ffffff; }}
QDoubleSpinBox#cartQtySpin QLineEdit {{ padding: 0px 1px; margin: 0px; min-height: 20px; background-color: transparent; color: #111827; border: none; font-weight: 600; font-size: 12px; }}
QWidget#cartQtyCell QPushButton#qtyAdjBtn {{ min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px; font-size: 15px; padding: 0; }}

QTableWidget, QTableView {{
    background-color: {_SCL};
    alternate-background-color: {_SBL};
    gridline-color: {_BC_L};
    border: 1px solid {_BC_L};
    border-radius: 14px;
}}
QTableWidget::item, QTableView::item {{ padding: 8px; border: none; }}
QTableWidget::item:selected, QTableView::item:selected {{ background-color: {_T_LOGIN_LIGHT}; color: {_T_LOGIN}; }}
QTableWidget::item:hover:!selected, QTableView::item:hover:!selected {{ background-color: {_NAV_HOVER_BG_L}; }}
QHeaderView::section {{ background-color: {_SEL}; color: #6B7280; padding: 10px 12px; border: none; border-bottom: 2px solid {_BC_L}; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.4px; }}

QWidget#dashboardInner {{ background-color: transparent; }}

QTabWidget::pane {{ border: 1px solid {_BC_L}; border-radius: 10px; background-color: {_SCL}; top: -1px; padding: 8px; }}
QTabBar::tab {{ background-color: {_SEL}; color: {_NAV_MUTED_FG_L}; border: 1px solid {_BC_L}; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; padding: 8px 16px; margin-right: 4px; }}
QTabBar::tab:selected {{ background-color: {_SCL}; color: {_T_LOGIN}; font-weight: 600; border-bottom: 2px solid {_NAV_ACCENT_L}; margin-bottom: -1px; }}
QTabBar::tab:hover:!selected {{ background-color: {_NAV_HOVER_BG_L}; color: #374151; }}

QTreeWidget {{ background-color: {_SEL}; alternate-background-color: {_SCL}; border: 1px solid {_BC_L}; border-radius: 10px; }}
QTreeWidget::item {{ padding: 6px 4px; }}
QTreeWidget::item:selected {{ background-color: {_T_LOGIN_LIGHT}; color: {_T_LOGIN}; }}
QTreeWidget::item:hover:!selected {{ background-color: {_NAV_HOVER_BG_L}; }}

QScrollBar:vertical {{ background: {_SEL}; width: 10px; margin: 4px 2px 4px 0; border-radius: 5px; }}
QScrollBar::handle:vertical {{ background: {_BC_L_S}; min-height: 36px; border-radius: 5px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: {_ACCENT}; }}
QScrollBar:horizontal {{ background: {_SEL}; height: 10px; margin: 0 4px 2px 4px; border-radius: 5px; }}
QScrollBar::handle:horizontal {{ background: {_BC_L_S}; border-radius: 5px; margin: 2px; }}
QScrollBar::handle:horizontal:hover {{ background: {_ACCENT}; }}

QCheckBox, QRadioButton {{ spacing: 10px; color: #374151; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 2px solid {_BC_L_S}; background-color: {_SCL}; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background-color: {_ACCENT}; border-color: {_ACCENT}; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {_ACCENT}; }}

QDialog {{ background-color: {_SBL}; }}
QTextEdit, QPlainTextEdit {{ background-color: {_SCL}; border: 1px solid {_BC_L_S}; border-radius: 8px; padding: 10px; color: #111827; }}
QDialogButtonBox QPushButton {{ min-width: 88px; }}

QLabel#shopLogo[logoState="image"] {{ border: 2px solid {_BC_L}; border-radius: 999px; background-color: {_SCL}; }}
QLabel#shopLogo[logoState="empty"] {{ border: 2px dashed {_BC_L_S}; border-radius: 999px; color: #6B7280; font-weight: 700; background-color: {_T_LOGIN_LIGHT}; }}
"""


def get_qt_stylesheet(appearance: str) -> str:
    """Return the full application QSS for the requested appearance."""
    if (appearance or "").strip().lower() == "light":
        return _LIGHT_QSS
    return _DARK_QSS


APPLIED_STYLESHEET = _DARK_QSS