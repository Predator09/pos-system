"""Persist shop branding (business name, logo, contact) locally."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional


def get_display_shop_name() -> str:
    """Name shown on sign-in, receipts, and in-app (from settings or ``config`` default)."""
    return ShopSettings().get_shop_name()


class ShopSettings:
    def __init__(self):
        from app.services.shop_context import logo_dir, shop_root

        shop_root().mkdir(parents=True, exist_ok=True)
        logo_dir().mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _settings_file() -> Path:
        from app.services.shop_context import shop_root

        return shop_root() / "shop_settings.json"

    @staticmethod
    def _logo_dir() -> Path:
        from app.services.shop_context import logo_dir

        return logo_dir()

    def _load(self) -> dict:
        p = self._settings_file()
        if not p.is_file():
            return {}
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        p = self._settings_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_logo_path(self) -> Optional[str]:
        path = self._load().get("logo_path")
        if not path:
            return None
        p = Path(path)
        return str(p) if p.is_file() else None

    def clear_logo(self) -> None:
        data = self._load()
        data.pop("logo_path", None)
        self._save(data)

    def set_logo_from_file(self, source_path: str) -> str:
        """Copy image into data/shop and store path. Returns stored path."""
        src = Path(source_path)
        if not src.is_file():
            raise ValueError("File not found")

        ext = src.suffix.lower() if src.suffix else ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
            ext = ".png"

        dest = self._logo_dir() / f"logo{ext}"
        shutil.copy2(src, dest)

        data = self._load()
        data["logo_path"] = str(dest.resolve())
        self._save(data)
        return str(dest.resolve())

    def get_shop_name(self) -> str:
        from app.config import SHOP_NAME

        raw = self._load().get("shop_name")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return SHOP_NAME

    def set_shop_name(self, name: str) -> str:
        n = (name or "").strip()
        if not n:
            raise ValueError("Business name cannot be empty.")
        n = n[:120]
        data = self._load()
        data["shop_name"] = n
        self._save(data)
        return n

    def get_business_phone(self) -> str:
        raw = self._load().get("business_phone")
        return raw.strip() if isinstance(raw, str) else ""

    def set_business_phone(self, value: str) -> None:
        v = (value or "").strip()[:80]
        data = self._load()
        if v:
            data["business_phone"] = v
        else:
            data.pop("business_phone", None)
        self._save(data)

    def get_business_email(self) -> str:
        raw = self._load().get("business_email")
        return raw.strip() if isinstance(raw, str) else ""

    def set_business_email(self, value: str) -> None:
        v = (value or "").strip()[:120]
        data = self._load()
        if v:
            data["business_email"] = v
        else:
            data.pop("business_email", None)
        self._save(data)

    def get_business_address(self) -> str:
        raw = self._load().get("business_address")
        return raw.strip() if isinstance(raw, str) else ""

    def set_business_address(self, value: str) -> None:
        v = (value or "").strip()[:500]
        data = self._load()
        if v:
            data["business_address"] = v
        else:
            data.pop("business_address", None)
        self._save(data)
