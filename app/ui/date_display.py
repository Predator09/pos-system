"""Human-facing dates as DD-MM-YYYY; storage and SQL stay ISO (YYYY-MM-DD)."""

from __future__ import annotations

from datetime import date, datetime

DISPLAY_DATE_FMT = "%d-%m-%Y"
DISPLAY_DATETIME_FMT = "%d-%m-%Y %H:%M:%S"


def format_iso_date_as_display(iso_10: str | None) -> str:
    """``YYYY-MM-DD`` → ``DD-MM-YYYY`` for labels and fields."""
    raw = str(iso_10 or "").strip()[:10]
    if len(raw) != 10:
        return str(iso_10 or "").strip()
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        return raw
    return d.strftime(DISPLAY_DATE_FMT)


def parse_date_input(s: str) -> str:
    """
    Parse a calendar day from the UI.

    Accepts ``DD-MM-YYYY`` (preferred) or legacy ``YYYY-MM-DD``.
    Returns ``YYYY-MM-DD`` for SQLite / services.
    """
    t = (s or "").strip()
    if not t:
        raise ValueError("Date is required.")
    if len(t) == 10 and t[4] == "-" and t[7] == "-":
        date.fromisoformat(t)
        return t
    if len(t) == 10 and t[2] == "-" and t[5] == "-":
        d = datetime.strptime(t, "%d-%m-%Y").date()
        return d.isoformat()
    raise ValueError("Use date format DD-MM-YYYY (e.g. 06-04-2026).")


def parse_expiry_input(s: str) -> str | None:
    """Empty → None; else same rules as ``parse_date_input``."""
    t = (s or "").strip()
    if not t:
        return None
    return parse_date_input(t)


def format_iso_datetime_for_display(raw: str | None) -> str:
    """Normalize stored ``YYYY-MM-DD[ T]HH:MM:SS`` strings to ``DD-MM-YYYY HH:MM:SS``."""
    s = str(raw or "").strip()
    if not s:
        return ""
    s = s.replace("T", " ", 1)
    if s.endswith("Z"):
        s = s[:-1].strip()
    if "." in s:
        i = s.index(".")
        if i >= 10:
            s = s[:i].strip()
    if len(s) >= 19 and s[10] == " " and s[4] == "-" and s[7] == "-":
        try:
            dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
            return dt.strftime(DISPLAY_DATETIME_FMT)
        except ValueError:
            return s[:19]
    if len(s) == 16 and s[10] == " " and s.count(":") == 2:
        try:
            dt = datetime.strptime(s[:16] + ":00", "%Y-%m-%d %H:%M:%S")
            return dt.strftime(DISPLAY_DATETIME_FMT)
        except ValueError:
            pass
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return format_iso_date_as_display(s)
    return s
