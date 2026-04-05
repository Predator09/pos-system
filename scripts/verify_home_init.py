#!/usr/bin/env python3
"""Smoke-test HomeScreen init (Tk + StringVars) without full app DB."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tkinter as tk

import ttkbootstrap as ttk

from app.ui.home import HomeScreen


class _FakeMain:
    """Minimal main window stand-in (HomeScreen expects .style and theme helpers)."""

    def __init__(self, window: ttk.Window):
        self._w = window
        self.current_user = {"username": "admin", "full_name": "Admin", "role": "owner"}

    @property
    def style(self):
        return self._w.style

    def get_current_theme(self) -> str:
        return self._w.style.theme_use()

    def apply_theme(self, name: str) -> bool:
        names = self._w.style.theme_names()
        if name not in names:
            return False
        self._w.style.theme_use(name)
        return True

    def apply_appearance(self, appearance: str) -> bool:
        from app.services.app_settings import AppSettings, theme_for_appearance

        name = theme_for_appearance(appearance)
        names = self._w.style.theme_names()
        if name not in names:
            return False
        self._w.style.theme_use(name)
        AppSettings().set_appearance(appearance)
        return True

    def show_screen(self, _name: str) -> None:
        pass


def main() -> None:
    root = ttk.Window(themename="superhero", title="verify")
    holder = ttk.Frame(root)
    holder.pack(fill=tk.BOTH, expand=True)
    HomeScreen(holder, _FakeMain(root))
    root.update_idletasks()
    root.destroy()
    print("HomeScreen init OK")


if __name__ == "__main__":
    main()
