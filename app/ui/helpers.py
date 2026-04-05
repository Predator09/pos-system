from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Any, Mapping, Optional

import customtkinter as ctk
import ttkbootstrap as ttk
from tkinter import messagebox

from app.config import CURRENCY_SYMBOL


def create_button(parent, text, command=None, **kwargs):
    return ctk.CTkButton(parent, text=text, command=command, **kwargs)


def create_entry(parent, textvariable=None, **kwargs):
    return ctk.CTkEntry(parent, textvariable=textvariable, **kwargs)


def format_money(amount: float) -> str:
    return f"{CURRENCY_SYMBOL} {amount:,.2f}"


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


def show_message(message: str, title: str = "POS", parent: Optional[tk.Misc] = None):
    if parent is not None:
        messagebox.showinfo(title, message, parent=parent)
    else:
        messagebox.showinfo(title, message)
