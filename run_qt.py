#!/usr/bin/env python3
"""Same as run.py — SmartStock PySide6 UI (kept for existing scripts and habits)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.entry_qt import main

if __name__ == "__main__":
    raise SystemExit(main())
