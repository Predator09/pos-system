"""Persist UI preferences (appearance + saved theme name for Qt shell)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from app import config as app_config
from app.runtime_paths import get_data_dir

AppearanceMode = Literal["dark", "light"]

THEME_DARK = "superhero"
THEME_LIGHT = "flatly"


def theme_for_appearance(mode: AppearanceMode | str) -> str:
    return THEME_DARK if mode == "dark" else THEME_LIGHT


class AppSettings:
    @staticmethod
    def _file() -> Path:
        return get_data_dir() / "app_settings.json"

    def _load(self) -> dict:
        path = self._file()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        path = self._file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
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

    def receipt_print_command_override(self) -> Optional[str]:
        """``None`` if the user has not saved an override in ``app_settings.json``."""
        data = self._load()
        if "receipt_print_command" not in data:
            return None
        v = data.get("receipt_print_command")
        if v is None:
            return ""
        return str(v)

    def get_receipt_print_command(self) -> str:
        """Effective command: saved override, else ``config.RECEIPT_PRINT_COMMAND``."""
        o = self.receipt_print_command_override()
        if o is not None:
            return o.strip()
        return (app_config.RECEIPT_PRINT_COMMAND or "").strip()

    def set_receipt_print_command_override(self, value: Optional[str]) -> None:
        """Persist override, or pass ``None`` to remove it (fall back to ``config.py``)."""
        data = self._load()
        if value is None:
            data.pop("receipt_print_command", None)
        else:
            data["receipt_print_command"] = value
        self._save(data)


def resolve_startup_theme() -> str:
    """Bootstrap theme name string from saved appearance (legacy helper; Qt uses ``get_appearance`` + QSS)."""
    chosen = theme_for_appearance(AppSettings().get_appearance())
    if chosen in (THEME_DARK, THEME_LIGHT):
        return chosen
    return (
        THEME_DARK
        if (app_config.THEME or "").lower() in ("superhero", "darkly", "cyborg")
        else THEME_LIGHT
    )
