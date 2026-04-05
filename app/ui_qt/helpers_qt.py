"""Qt helpers; business formatting reused from existing UI helpers."""

from PySide6.QtWidgets import QMessageBox, QWidget

from app.ui.helpers import format_money as _format_money

# Re-export for views that expect the same name
format_money = _format_money


def info_message(parent: QWidget | None, title: str, text: str) -> None:
    QMessageBox.information(parent, title, text)


def warning_message(parent: QWidget | None, title: str, text: str) -> None:
    QMessageBox.warning(parent, title, text)


def ask_yes_no(parent: QWidget | None, title: str, text: str) -> bool:
    r = QMessageBox.question(parent, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    return r == QMessageBox.Yes


def ask_yes_no_cancel(parent: QWidget | None, title: str, text: str):
    """Return QMessageBox.Yes, No, or Cancel."""
    return QMessageBox.question(
        parent,
        title,
        text,
        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        QMessageBox.Yes,
    )
