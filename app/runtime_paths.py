"""Writable application data directory: project ``data/`` in dev, %LOCALAPPDATA%\\SmartStock when frozen."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app.config import APP_NAME

# Folder name under LOCALAPPDATA (ASCII, no spaces — safe for paths).
_DATA_FOLDER = APP_NAME.replace(" ", "")


def get_data_dir() -> Path:
    """
    Root for SQLite, ``app_settings.json``, ``shops/``, legacy migration sources.

    - **Development:** ``<pos-system>/data`` (next to the repo, same as before).
    - **PyInstaller:** ``%LOCALAPPDATA%\\<AppName>`` so the DB stays writable even when
      the ``.exe`` lives under Program Files.
    """
    if getattr(sys, "frozen", False):
        local = os.environ.get("LOCALAPPDATA")
        if local:
            root = Path(local) / _DATA_FOLDER
        else:
            root = Path(sys.executable).resolve().parent / _DATA_FOLDER
        root.mkdir(parents=True, exist_ok=True)
        return root
    return Path(__file__).resolve().parent.parent / "data"
