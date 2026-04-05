#!/usr/bin/env python3
"""Launch the POS app with the PySide6 UI (Tk UI unchanged — use run.py for Tk)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.database.connection import db
from app.database.migrations import DatabaseMigrations
from app.services.app_settings import AppSettings
from app.ui_qt.main_window import MainQtWindow
from app.ui_qt.styles import get_qt_stylesheet


def main() -> None:
    migrations = DatabaseMigrations(db)
    migrations.init_database()
    db.connect()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 11))
    app.setStyleSheet(get_qt_stylesheet(AppSettings().get_appearance()))
    win = MainQtWindow()
    win.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
