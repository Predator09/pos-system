from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from app.config import CURRENCY_SYMBOL
from app.ui.date_display import DISPLAY_DATETIME_FMT, format_iso_datetime_for_display


def format_money(amount: float) -> str:
    return f"{CURRENCY_SYMBOL} {amount:,.2f}"


def format_purchase_timestamp(value: Any) -> str:
    """Format receipt / purchase time for lists (date as DD-MM-YYYY when parseable)."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime(DISPLAY_DATETIME_FMT)
    s = str(value).strip()
    if not s:
        return ""
    s = s.replace("T", " ", 1)
    if s.endswith("Z"):
        s = s[:-1].strip()
    if "." in s:
        i = s.index(".")
        if i >= 10:
            s = s[:i].strip()
    if len(s) >= 19 and s[10] == " ":
        return format_iso_datetime_for_display(s[:19])
    if len(s) == 16 and s[10] == " " and s.count(":") == 2:
        return format_iso_datetime_for_display(f"{s}:00")
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return format_iso_datetime_for_display(f"{s} 00:00:00")
    return format_iso_datetime_for_display(s)


def welcome_first_name(user: Mapping[str, Any] | None) -> str:
    """First name from full_name, else username, else a friendly fallback."""
    u = user or {}
    full = (u.get("full_name") or "").strip()
    if full:
        return full.split()[0]
    un = (u.get("username") or "").strip()
    return un if un else "there"


def welcome_time_greeting() -> str:
    h = datetime.now().hour
    if h < 12:
        return "Good morning"
    if h < 18:
        return "Good afternoon"
    return "Good evening"


def home_welcome_status_line(user: Mapping[str, Any] | None, shop_name: str) -> str:
    """Short line for the home status strip (seen right after sign-in)."""
    first = welcome_first_name(user)
    g = welcome_time_greeting()
    return f"{g}, {first}! Welcome to {shop_name}."


def home_welcome_detail_line(user: Mapping[str, Any] | None, shop_name: str) -> str:
    """Warmer secondary welcome on the home hero / session card."""
    first = welcome_first_name(user)
    g = welcome_time_greeting()
    return (
        f"{g}, {first}. Great to have you with us at {shop_name} today — "
        "your live stats are right here; use the sidebar for register, products, and more."
    )
