"""Design tokens — reference palette for the POS UI (Qt QSS + shared constants)."""

from __future__ import annotations

from typing import Final

# Layered surfaces (Qt shell — base canvas, cards, elevated/table chrome)
SURFACE_BASE_LIGHT: Final[str] = "#f8fafc"
SURFACE_CARD_LIGHT: Final[str] = "#ffffff"
SURFACE_ELEVATED_LIGHT: Final[str] = "#e2e8f0"

SURFACE_BASE_DARK: Final[str] = "#0F172A"
SURFACE_CARD_DARK: Final[str] = "#1E293B"
SURFACE_ELEVATED_DARK: Final[str] = "#334155"


class UIThemeTokens:
    """Brand and semantic colors (hex, sRGB) shared by Tk + Qt."""

    PRIMARY: Final[str] = "#2563EB"
    PRIMARY_HOVER: Final[str] = "#1E4ED8"
    PRIMARY_MUTED: Final[str] = "#1D4ED8"
    SUCCESS: Final[str] = "#22C55E"
    SUCCESS_HOVER: Final[str] = "#22c55e"
    WARNING: Final[str] = "#F59E0B"
    DANGER: Final[str] = "#EF4444"
    # App canvas — aligned with layered surfaces
    BG_LIGHT: Final[str] = SURFACE_BASE_LIGHT
    BG_DARK: Final[str] = SURFACE_BASE_DARK
    TEXT_LIGHT: Final[str] = "#212529"
    TEXT_DARK: Final[str] = "#F8FAFC"


TOKENS = UIThemeTokens

# Optional mapping of semantic roles to style roots (legacy / docs).
BOOTSTYLE_BY_ROLE: dict[str, str] = {
    "primary": "primary",
    "success": "success",
    "warning": "warning",
    "danger": "danger",
    "neutral": "secondary",
}

# Label text colors (light / dark appearance tuples) — used where noted in Qt/Tk-era labels.
CTK_TEXT_MUTED: Final[tuple[str, str]] = ("#5c636a", "#adb5bd")
CTK_TEXT_SUCCESS: Final[tuple[str, str]] = ("#198754", "#75b798")
CTK_TEXT_DANGER: Final[tuple[str, str]] = ("#c1121f", "#f1aeb5")
CTK_TEXT_INFO: Final[tuple[str, str]] = ("#0b5ed7", "#6ea8fe")
CTK_TEXT_WARN: Final[tuple[str, str]] = ("#cc8500", "#ffcd39")

# Inventory table row tint (ttk.Treeview tags) — dark charcoal lists; WCAG-ish contrast on text.
PRODUCT_ROW_INACTIVE_BG: Final[str] = "#3d3518"
PRODUCT_ROW_INACTIVE_FG: Final[str] = "#fbbf24"
PRODUCT_ROW_EXPIRED_BG: Final[str] = "#421a1a"
PRODUCT_ROW_EXPIRED_FG: Final[str] = "#fecaca"
# In-stock “normal” rows: elevated / card surfaces (matches layered Qt tables)
PRODUCT_ROW_ACTIVE_OK_BG_LIGHT: Final[str] = SURFACE_CARD_LIGHT
PRODUCT_ROW_ACTIVE_OK_BG_DARK: Final[str] = SURFACE_ELEVATED_DARK
PRODUCT_ROW_ACTIVE_OK_FG_LIGHT: Final[str] = "#000000"
PRODUCT_ROW_ACTIVE_OK_FG_DARK: Final[str] = "#e2e8f0"
PRODUCT_STATUS_INACTIVE_QT_BG: Final[str] = "#78350f"
PRODUCT_STATUS_INACTIVE_QT_FG: Final[str] = "#fef3c7"
PRODUCT_STATUS_EXPIRED_QT_BG: Final[str] = "#7f1d1d"
PRODUCT_STATUS_EXPIRED_QT_FG: Final[str] = "#fecaca"


def product_active_row_surface(appearance: str) -> tuple[str, str]:
    """Background and foreground for healthy in-stock inventory rows (Tk tags + Qt table items)."""
    if (appearance or "").lower() == "dark":
        return PRODUCT_ROW_ACTIVE_OK_BG_DARK, PRODUCT_ROW_ACTIVE_OK_FG_DARK
    return PRODUCT_ROW_ACTIVE_OK_BG_LIGHT, PRODUCT_ROW_ACTIVE_OK_FG_LIGHT


# --- CustomTkinter shell (light / dark appearance tuples) ---
CTK_CARD_BORDER: Final[tuple[str, str]] = ("#e2e8f0", "#334155")
CTK_CARD_BORDER_STRONG: Final[tuple[str, str]] = ("#cbd5e1", "#334155")
CTK_BTN_PRIMARY_FG: Final[tuple[str, str]] = ("#2563EB", "#2563EB")
CTK_BTN_PRIMARY_HOVER: Final[tuple[str, str]] = ("#1E4ED8", "#1E4ED8")
CTK_BTN_GHOST_BORDER: Final[tuple[str, str]] = ("#94a3b8", "#475569")
CTK_BTN_GHOST_HOVER: Final[tuple[str, str]] = ("#f1f5f9", "#1e293b")

# Main window top nav pills
CTK_NAV_SELECTED_FG: Final[tuple[str, str]] = ("#1D4ED8", "#2563EB")
CTK_NAV_SELECTED_HOVER: Final[tuple[str, str]] = ("#1E40AF", "#1E4ED8")
CTK_NAV_SALES_SELECTED: Final[tuple[str, str]] = ("#15803d", "#22c55e")
CTK_NAV_SALES_HOVER: Final[tuple[str, str]] = ("#166534", "#4ade80")
CTK_NAV_BORDER_ACCENT: Final[tuple[str, str]] = ("#2563EB", "#2563EB")
CTK_NAV_BORDER_SALES: Final[tuple[str, str]] = ("#16a34a", "#4ade80")
CTK_NAV_BORDER_MUTED: Final[tuple[str, str]] = ("#cbd5e1", "#475569")
CTK_NAV_TEXT_MUTED: Final[tuple[str, str]] = ("#64748b", "#94A3B8")
CTK_NAV_HOVER_SURFACE: Final[tuple[str, str]] = ("#f1f5f9", "#334155")
CTK_HEADER_ACCENT_TEXT: Final[tuple[str, str]] = ("#0f766e", "#5eead4")
