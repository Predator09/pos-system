"""Qt helpers; business formatting reused from existing UI helpers."""

from PySide6.QtWidgets import QWidget

from app.services.dialog_service import DialogButton, DialogService
from app.ui.helpers import format_money as _format_money

# Re-export for views that expect the same name
format_money = _format_money


def info_message(parent: QWidget | None, title: str, text: str) -> None:
    DialogService.info(title, text, parent=parent)


def warning_message(parent: QWidget | None, title: str, text: str) -> None:
    DialogService.warning(title, text, parent=parent)


def ask_yes_no(parent: QWidget | None, title: str, text: str) -> bool:
    return DialogService.question_yes_no(title, text, parent=parent, default_yes=False)


def ask_yes_no_cancel(parent: QWidget | None, title: str, text: str) -> DialogButton:
    """Return :class:`DialogButton` YES, NO, or CANCEL."""
    return DialogService.question_yes_no_cancel(title, text, parent=parent)
