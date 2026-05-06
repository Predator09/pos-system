"""theme_tokens.py — GamMarket POS design token reference.

Single source of truth for every colour, surface, and semantic role
used across the Qt UI (QSS stylesheets), chart widgets, and legacy Tk
shell.

Palette story
─────────────
Primary brand   → teal ramp  (#0D3B38 → #1DB39E → #EEF7F5)
Neutral surface → warm grey  (#F0F4F3 → #FFFFFF)
Warning         → amber      (#F59E0B)
Danger          → red        (#EF4444)
Info            → blue       (#3B82F6)
Success         → teal (same as brand accent)

All hex values are sRGB.  Lightness thresholds for dark-mode detection:
  QPalette.Window.lightness() < 140  →  dark mode active.
"""

from __future__ import annotations

from typing import Final


# ── Layered surfaces ───────────────────────────────────────────────────────
# Used by chart widgets (grid colour, card background) and table chrome.

SURFACE_BASE_LIGHT:     Final[str] = "#F0F4F3"   # page canvas
SURFACE_CARD_LIGHT:     Final[str] = "#FFFFFF"   # card / panel background
SURFACE_ELEVATED_LIGHT: Final[str] = "#E2E8E6"   # table header, dividers

SURFACE_BASE_DARK:      Final[str] = "#0A1F1D"   # page canvas (dark)
SURFACE_CARD_DARK:      Final[str] = "#132E2B"   # card background (dark)
SURFACE_ELEVATED_DARK:  Final[str] = "#1E4540"   # table header, dividers (dark)


# ── Brand teal ramp ────────────────────────────────────────────────────────

TEAL_900: Final[str] = "#0D3B38"   # darkest — nav background, bold text
TEAL_700: Final[str] = "#155652"   # mid-dark — hover states
TEAL_600: Final[str] = "#167A6A"   # primary button fill
TEAL_500: Final[str] = "#1A9680"   # button hover
TEAL_400: Final[str] = "#1DB39E"   # accent — borders, active pills, icons
TEAL_100: Final[str] = "#EEF7F5"   # lightest fill — chip backgrounds, row tints
TEAL_50:  Final[str] = "#F5FBF9"   # near-white teal tint


# ── Semantic colours ───────────────────────────────────────────────────────

AMBER_BG:  Final[str] = "#FFFBEB"
AMBER_BR:  Final[str] = "#F59E0B"
AMBER_TXT: Final[str] = "#92400E"

RED_BG:    Final[str] = "#FEF2F2"
RED_BR:    Final[str] = "#EF4444"
RED_TXT:   Final[str] = "#991B1B"

BLUE_BG:   Final[str] = "#EFF6FF"
BLUE_BR:   Final[str] = "#3B82F6"
BLUE_TXT:  Final[str] = "#1E40AF"

GREEN_BG:  Final[str] = TEAL_100
GREEN_BR:  Final[str] = TEAL_400
GREEN_TXT: Final[str] = TEAL_600


# ── Text colours ───────────────────────────────────────────────────────────

TEXT_PRIMARY:   Final[str] = "#111827"
TEXT_SECONDARY: Final[str] = "#374151"
TEXT_MUTED:     Final[str] = "#6B7280"
TEXT_INVERSE:   Final[str] = "#F8FAFC"   # text on dark surfaces


# ── UIThemeTokens class ────────────────────────────────────────────────────
# Kept for backwards-compatibility — code that imports TOKENS.PRIMARY etc.
# continues to work unchanged; values now point to the teal palette.

class UIThemeTokens:
    """Brand and semantic colours shared by Qt widgets and chart painters."""

    # Primary brand (previously blue — now teal)
    PRIMARY:         Final[str] = TEAL_600
    PRIMARY_HOVER:   Final[str] = TEAL_500
    PRIMARY_MUTED:   Final[str] = TEAL_700

    # Semantic
    SUCCESS:         Final[str] = TEAL_400
    SUCCESS_HOVER:   Final[str] = TEAL_500
    WARNING:         Final[str] = AMBER_BR
    DANGER:          Final[str] = RED_BR
    INFO:            Final[str] = BLUE_BR

    # App canvas
    BG_LIGHT:        Final[str] = SURFACE_BASE_LIGHT
    BG_DARK:         Final[str] = SURFACE_BASE_DARK

    # Text
    TEXT_LIGHT:      Final[str] = TEXT_PRIMARY
    TEXT_DARK:       Final[str] = TEXT_INVERSE

    # Accent
    ACCENT:          Final[str] = TEAL_400
    ACCENT_LIGHT:    Final[str] = TEAL_100


TOKENS = UIThemeTokens


# ── Semantic role → style root (legacy / docs) ─────────────────────────────

BOOTSTYLE_BY_ROLE: dict[str, str] = {
    "primary": "primary",
    "success": "success",
    "warning": "warning",
    "danger":  "danger",
    "neutral": "secondary",
}


# ── Label text colours (light / dark tuples) ──────────────────────────────
# Used by Qt and legacy Tk labels that accept (light_hex, dark_hex) tuples.

CTK_TEXT_MUTED:   Final[tuple[str, str]] = (TEXT_MUTED,   "#94A3B8")
CTK_TEXT_SUCCESS: Final[tuple[str, str]] = (TEAL_600,     TEAL_400)
CTK_TEXT_DANGER:  Final[tuple[str, str]] = (RED_TXT,      "#F1AEBB")
CTK_TEXT_INFO:    Final[tuple[str, str]] = (BLUE_TXT,     "#6EA8FE")
CTK_TEXT_WARN:    Final[tuple[str, str]] = (AMBER_TXT,    "#FFCD39")


# ── Inventory table row tints ──────────────────────────────────────────────
# Treeview tags (Tk) and QTableWidgetItem colours (Qt).

PRODUCT_ROW_INACTIVE_BG: Final[str] = "#2D2A14"
PRODUCT_ROW_INACTIVE_FG: Final[str] = AMBER_BR

PRODUCT_ROW_EXPIRED_BG:  Final[str] = "#2D1414"
PRODUCT_ROW_EXPIRED_FG:  Final[str] = "#FECACA"

# In-stock "normal" rows — aligned with layered surfaces
PRODUCT_ROW_ACTIVE_OK_BG_LIGHT: Final[str] = SURFACE_CARD_LIGHT
PRODUCT_ROW_ACTIVE_OK_BG_DARK:  Final[str] = SURFACE_ELEVATED_DARK
PRODUCT_ROW_ACTIVE_OK_FG_LIGHT: Final[str] = TEXT_PRIMARY
PRODUCT_ROW_ACTIVE_OK_FG_DARK:  Final[str] = TEXT_INVERSE

# Qt-specific status badge backgrounds (used in product table item delegates)
PRODUCT_STATUS_INACTIVE_QT_BG: Final[str] = AMBER_BG
PRODUCT_STATUS_INACTIVE_QT_FG: Final[str] = AMBER_TXT
PRODUCT_STATUS_EXPIRED_QT_BG:  Final[str] = RED_BG
PRODUCT_STATUS_EXPIRED_QT_FG:  Final[str] = RED_TXT


def product_active_row_surface(appearance: str) -> tuple[str, str]:
    """Background and foreground for healthy in-stock inventory rows."""
    if (appearance or "").lower() == "dark":
        return PRODUCT_ROW_ACTIVE_OK_BG_DARK, PRODUCT_ROW_ACTIVE_OK_FG_DARK
    return PRODUCT_ROW_ACTIVE_OK_BG_LIGHT, PRODUCT_ROW_ACTIVE_OK_FG_LIGHT


# ── CustomTkinter shell tokens (light / dark tuples) ──────────────────────
# Legacy Tk shell — kept for backwards-compatibility.

CTK_CARD_BORDER:        Final[tuple[str, str]] = (SURFACE_ELEVATED_LIGHT, SURFACE_ELEVATED_DARK)
CTK_CARD_BORDER_STRONG: Final[tuple[str, str]] = ("#C8D4D2",              SURFACE_ELEVATED_DARK)

CTK_BTN_PRIMARY_FG:     Final[tuple[str, str]] = (TEAL_600, TEAL_400)
CTK_BTN_PRIMARY_HOVER:  Final[tuple[str, str]] = (TEAL_500, TEAL_500)
CTK_BTN_GHOST_BORDER:   Final[tuple[str, str]] = ("#A0AEC0", "#4A5568")
CTK_BTN_GHOST_HOVER:    Final[tuple[str, str]] = (TEAL_100,  SURFACE_CARD_DARK)

# Top-nav pills
CTK_NAV_SELECTED_FG:    Final[tuple[str, str]] = (TEAL_600,  TEAL_400)
CTK_NAV_SELECTED_HOVER: Final[tuple[str, str]] = (TEAL_700,  TEAL_500)
CTK_NAV_SALES_SELECTED: Final[tuple[str, str]] = (TEAL_600,  TEAL_400)
CTK_NAV_SALES_HOVER:    Final[tuple[str, str]] = (TEAL_700,  TEAL_500)
CTK_NAV_BORDER_ACCENT:  Final[tuple[str, str]] = (TEAL_400,  TEAL_400)
CTK_NAV_BORDER_SALES:   Final[tuple[str, str]] = (TEAL_600,  TEAL_400)
CTK_NAV_BORDER_MUTED:   Final[tuple[str, str]] = (SURFACE_ELEVATED_LIGHT, "#4A5568")
CTK_NAV_TEXT_MUTED:     Final[tuple[str, str]] = (TEXT_MUTED,             "#94A3B8")
CTK_NAV_HOVER_SURFACE:  Final[tuple[str, str]] = (TEAL_100,               SURFACE_CARD_DARK)
CTK_HEADER_ACCENT_TEXT: Final[tuple[str, str]] = (TEAL_700,               TEAL_400)
