# App
APP_NAME = "POS System"
VERSION = "1.0.0"

# Database
DATABASE_PATH = "data/pos_system.db"

# UI
WINDOW_TITLE = "POS System - Offline"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
THEME = "superhero"  # default dark; paired with light "flatly" via appearance toggle

# Fonts
TITLE_FONT = ("Helvetica", 20, "bold")
HEADER_FONT = ("Helvetica", 14, "bold")
BODY_FONT = ("Helvetica", 11)
SMALL_FONT = ("Helvetica", 9)

# Spacing
PAD_SM = 5
PAD_MD = 10
PAD_LG = 15

# Business (default until changed on sign-in → ``data/shop_settings.json``)
SHOP_NAME = "Brikama Mini Mart"
CURRENCY = "GMD"
CURRENCY_SYMBOL = "GMD"

# Receipts: optional shell command (receipt UTF-8 on stdin). If empty, uses OS print hook.
RECEIPT_PRINT_COMMAND = ""
RECEIPT_ARCHIVE_DIR = "data/receipts"


def format_app_footer_text() -> str:
    """Single line for main-window status/footer (shop name from settings when available)."""
    from app.services.shop_settings import get_display_shop_name

    return f"{APP_NAME} v{VERSION} · {get_display_shop_name()} · Offline-first · Local database"
