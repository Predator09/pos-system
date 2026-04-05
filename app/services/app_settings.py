"""Persist UI preferences (appearance + ttkbootstrap theme name)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from app import config as app_config

AppearanceMode = Literal["dark", "light"]

THEME_DARK = "superhero"
THEME_LIGHT = "flatly"


def theme_for_appearance(mode: AppearanceMode | str) -> str:
    return THEME_DARK if mode == "dark" else THEME_LIGHT


class AppSettings:
    _FILE = Path("data/app_settings.json")

    def _load(self) -> dict:
        self._FILE.parent.mkdir(parents=True, exist_ok=True)
        if not self._FILE.is_file():
            return {}
        try:
            with open(self._FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        self._FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self._FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_appearance(self) -> AppearanceMode:
        data = self._load()
        if data.get("appearance") in ("dark", "light"):
            return data["appearance"]
        # Migrate legacy `theme` key → appearance
        legacy = data.get("theme")
        if legacy == THEME_DARK or legacy in ("darkly", "cyborg", "vapor", "solar", "superhero"):
            return "dark"
        if legacy == THEME_LIGHT or legacy in ("flatly", "cosmo", "litera", "minty", "pulse", "sandstone", "united", "yeti", "morph"):
            return "light"
        return "dark" if (app_config.THEME or "").lower() in ("superhero", "darkly", "cyborg") else "light"

    def set_appearance(self, mode: AppearanceMode) -> None:
        data = self._load()
        data["appearance"] = mode
        data["theme"] = theme_for_appearance(mode)
        self._save(data)

    def get_theme(self) -> Optional[str]:
        return self._load().get("theme")

    def set_theme(self, theme_name: str) -> None:
        data = self._load()
        data["theme"] = theme_name
        if theme_name == THEME_DARK:
            data["appearance"] = "dark"
        elif theme_name == THEME_LIGHT:
            data["appearance"] = "light"
        self._save(data)


def resolve_startup_theme() -> str:
    """ttkbootstrap theme for Window(themename=...) from saved appearance.

    Must not call ``ttk.Style()`` here: that runs while resolving ``MainWindow(...)``
    arguments, *before* ``Tk.__init__`` completes. On Python 3.14 that can create a
    stray ``Tk`` and leave ``tkinter._default_root`` on the wrong interpreter, which
    later breaks ``ImageTk.PhotoImage`` during ``theme_use``.
    """
    chosen = theme_for_appearance(AppSettings().get_appearance())
    if chosen in (THEME_DARK, THEME_LIGHT):
        return chosen
    return (
        THEME_DARK
        if (app_config.THEME or "").lower() in ("superhero", "darkly", "cyborg")
        else THEME_LIGHT
    )
