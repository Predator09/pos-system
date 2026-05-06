import importlib
import os
import pkgutil
import re

# App
APP_NAME = "SmartStock"
APP_VERSION = "1.1.0"


def get_app_version() -> str:
    """Return the application semantic version string."""
    return APP_VERSION


def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a dotted version string (e.g. ``1.2.3`` or ``v1.2.3``) into a tuple of integers."""
    s = (version_str or "").strip()
    if s[:1] in ("v", "V"):
        s = s[1:].strip()
    if not s:
        raise ValueError("version string is empty")
    parts = s.split(".")
    return tuple(int(p) for p in parts)


def safe_parse_version(version_str: str) -> tuple[int, ...]:
    """Like :func:`parse_version`, but return ``(0, 0, 0)`` if parsing fails (and log a warning)."""
    try:
        return parse_version(version_str)
    except (TypeError, ValueError) as exc:
        from app.services.app_logging import get_logger

        get_logger().warning(
            "safe_parse_version: invalid version string %r (%s); using (0, 0, 0)",
            version_str,
            exc,
        )
        return (0, 0, 0)


def is_newer_version(v1: str, v2: str) -> bool:
    """Return True if version *v1* is strictly greater than *v2* (numeric dotted segments)."""
    a = parse_version(v1)
    b = parse_version(v2)
    n = max(len(a), len(b))
    a_pad = a + (0,) * (n - len(a))
    b_pad = b + (0,) * (n - len(b))
    return a_pad > b_pad


# Backward-compatible alias (same value as ``APP_VERSION``).
VERSION = APP_VERSION

def compute_max_supported_db_version() -> str:
    """Derive max supported ``db_version`` from available ``mNNN_*`` migration modules."""
    package = importlib.import_module("app.database.migrations")
    max_n = 0
    for module_info in pkgutil.iter_modules(package.__path__):
        m = re.match(r"^m(\d+)_", module_info.name, flags=re.IGNORECASE)
        if not m:
            continue
        n = int(m.group(1))
        if n > max_n:
            max_n = n
    return f"0.0.{max_n}"


# Highest ``db_version`` stored in ``app_metadata`` that this build can open.
# If the database label is newer, startup exits (DB from a newer SmartStock).
# Computed from available ``mNNN_*`` migration modules.
MAX_SUPPORTED_DB_VERSION = compute_max_supported_db_version()

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

    return f"{APP_NAME} v{get_app_version()} · {get_display_shop_name()} · Offline-first · Local database"
