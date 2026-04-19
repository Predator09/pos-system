"""Launch SmartStock (PySide6 UI)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.config import APP_NAME
from app.database.connection import db
from app.database.migrations import DatabaseMigrations
from app.services.app_settings import AppSettings
from app.services.install_code_gate import ensure_install_code
from app.ui_qt.main_window import MainQtWindow
from app.ui_qt.styles import get_qt_stylesheet


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 14))
    app.setStyleSheet(get_qt_stylesheet(AppSettings().get_appearance()))
    if not ensure_install_code():
        return 0

    migrations = DatabaseMigrations(db)
    migrations.init_database()
    db.connect()

    win = MainQtWindow()
    win.show()
    return app.exec()
