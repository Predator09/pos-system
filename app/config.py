import os

# App
APP_NAME = "SmartStock"
VERSION = "1.0.0"

# Install gate secret (same value as ``INSTALL_CODE`` in ``installer/SmartStock.iss``):
# - Prefer ``SMARTSTOCK_INSTALL_CODE_SHA256`` (hex digest of the code).
# - Fallback to ``SMARTSTOCK_INSTALL_CODE`` (plain text).
INSTALL_CODE_REQUIRED_SHA256 = (os.getenv("SMARTSTOCK_INSTALL_CODE_SHA256") or "").strip().lower()
INSTALL_CODE_REQUIRED = (os.getenv("SMARTSTOCK_INSTALL_CODE") or "AlhamdulilA").strip()

# Re-prompt for the same code after this many days (approx. two months).
try:
    INSTALL_CODE_REVERIFY_INTERVAL_DAYS = int((os.getenv("SMARTSTOCK_INSTALL_REVERIFY_DAYS") or "60").strip())
except ValueError:
    INSTALL_CODE_REVERIFY_INTERVAL_DAYS = 60

# Database (legacy flat file; live DB is under ``data/shops/<shop_id>/`` — see ``runtime_paths.get_data_dir``)
DATABASE_PATH = "data/pos_system.db"  # relative only for docs; use ``shop_context.database_path()`` in code

# UI
WINDOW_TITLE = "SmartStock — Offline"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
THEME = "superhero"  # default dark; paired with light "flatly" via appearance toggle

# Fonts
TITLE_FONT = ("Helvetica", 20, "bold")
HEADER_FONT = ("Helvetica", 14, "bold")
BODY_FONT = ("Helvetica", 11)
SMALL_FONT = ("Helvetica", 9)

# Spacing
PAD_SM = 8
PAD_MD = 16
PAD_LG = 24

# Business (default until changed on sign-in → ``data/shop_settings.json``)
SHOP_NAME = "My shop"
CURRENCY = "GMD"
CURRENCY_SYMBOL = "GMD"

# Receipts: optional shell command (receipt UTF-8 on stdin). If empty, uses OS print hook.
# Users can override per device from Settings → Receipts (stored in app_settings.json).
RECEIPT_PRINT_COMMAND = ""
RECEIPT_ARCHIVE_DIR = "data/receipts"  # per-shop receipts use ``shop_context.receipts_dir()``


def format_app_footer_text() -> str:
    """Single line for main-window status/footer (shop name from settings when available)."""
    from app.services.shop_settings import get_display_shop_name

    return f"{APP_NAME} v{VERSION} · {get_display_shop_name()} · Offline-first · Local database"
