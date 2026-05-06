"""
Versioned migration modules (``m001_*``, ``m002_*``, …) with ``run(db_connection)``.

Legacy schema bootstrap remains in the sibling file ``../migrations.py`` (``DatabaseMigrations``).
This package shadows that module name; we re-export ``DatabaseMigrations`` for compatibility.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_LEGACY = Path(__file__).resolve().parent.parent / "migrations.py"
_spec = importlib.util.spec_from_file_location(
    "app.database._legacy_migrations_module",
    _LEGACY,
)
assert _spec is not None and _spec.loader is not None
_legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy)

DatabaseMigrations = _legacy.DatabaseMigrations

__all__ = ["DatabaseMigrations"]
