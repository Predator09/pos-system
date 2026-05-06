"""Centralized modal dialogs (widget-based; avoids native QMessageBox issues on some setups)."""

from __future__ import annotations

import sys
from collections.abc import Callable
from enum import IntEnum
from typing import TypeVar

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.app_logging import get_logger

_T = TypeVar("_T")


class DialogButton(IntEnum):
    """Return values for :meth:`DialogService.question_yes_no_cancel`."""

    YES = 1
    NO = 2
    CANCEL = 3


class DialogService:
    @staticmethod
    def _print_fallback(title: str, message: str) -> None:
        print(f"{title}\n{message}", file=sys.stderr, flush=True)

    @staticmethod
    def _safe_run(
        kind: str,
        title: str,
        message: str,
        fn: Callable[[], _T],
        *,
        on_fail: _T,
    ) -> _T:
        try:
            return fn()
        except Exception:
            get_logger().exception("DialogService.%s failed (title=%r)", kind, title)
            DialogService._print_fallback(title, message)
            return on_fail

    @staticmethod
    def error(title: str, message: str, *, parent: QWidget | None = None) -> None:
        DialogService._safe_run(
            "error",
            title,
            message,
            lambda: DialogService._plain_message(parent, title, message),
            on_fail=None,
        )

    @staticmethod
    def warning(title: str, message: str, *, parent: QWidget | None = None) -> None:
        DialogService._safe_run(
            "warning",
            title,
            message,
            lambda: DialogService._plain_message(parent, title, message),
            on_fail=None,
        )

    @staticmethod
    def info(title: str, message: str, *, parent: QWidget | None = None) -> None:
        DialogService._safe_run(
            "info",
            title,
            message,
            lambda: DialogService._plain_message(parent, title, message),
            on_fail=None,
        )

    @staticmethod
    def _plain_message(parent: QWidget | None, title: str, text: str) -> None:
        dlg = QDialog(parent)
        dlg.setWindowTitle(title)
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        btn = QPushButton("OK")
        btn.setDefault(True)
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)

        def on_reject_handler() -> None:
            pass

        dlg.rejected.connect(on_reject_handler)
        dlg.exec()

    @staticmethod
    def question_yes_no(
        title: str,
        message: str,
        *,
        parent: QWidget | None = None,
        default_yes: bool = False,
    ) -> bool:
        """Return True if Yes was clicked, False if No."""

        def _run() -> bool:
            dlg = QDialog(parent)
            dlg.setWindowTitle(title)
            dlg.setModal(True)
            root = QVBoxLayout(dlg)
            lbl = QLabel(message)
            lbl.setWordWrap(True)
            root.addWidget(lbl)
            row = QHBoxLayout()
            yes_btn = QPushButton("Yes")
            no_btn = QPushButton("No")
            row.addStretch(1)
            row.addWidget(yes_btn)
            row.addWidget(no_btn)
            root.addLayout(row)

            result = {"v": False}

            def on_yes() -> None:
                result["v"] = True
                dlg.accept()

            def on_no() -> None:
                result["v"] = False
                dlg.accept()

            def on_reject_handler() -> None:
                result["v"] = False

            yes_btn.clicked.connect(on_yes)
            no_btn.clicked.connect(on_no)
            dlg.rejected.connect(on_reject_handler)
            if default_yes:
                yes_btn.setDefault(True)
            else:
                no_btn.setDefault(True)
            dlg.exec()
            return bool(result["v"])

        return DialogService._safe_run("question_yes_no", title, message, _run, on_fail=False)

    @staticmethod
    def question_yes_cancel(
        title: str,
        message: str,
        *,
        parent: QWidget | None = None,
        default_yes: bool = False,
    ) -> bool:
        """Return True if Yes was clicked, False if Cancel."""

        def _run() -> bool:
            dlg = QDialog(parent)
            dlg.setWindowTitle(title)
            dlg.setModal(True)
            root = QVBoxLayout(dlg)
            lbl = QLabel(message)
            lbl.setWordWrap(True)
            root.addWidget(lbl)
            row = QHBoxLayout()
            yes_btn = QPushButton("Yes")
            cancel_btn = QPushButton("Cancel")
            row.addStretch(1)
            row.addWidget(yes_btn)
            row.addWidget(cancel_btn)
            root.addLayout(row)

            result = {"v": False}

            def on_yes() -> None:
                result["v"] = True
                dlg.accept()

            def on_cancel() -> None:
                result["v"] = False
                dlg.accept()

            def on_reject_handler() -> None:
                result["v"] = False

            yes_btn.clicked.connect(on_yes)
            cancel_btn.clicked.connect(on_cancel)
            dlg.rejected.connect(on_reject_handler)
            if default_yes:
                yes_btn.setDefault(True)
            else:
                cancel_btn.setDefault(True)
            dlg.exec()
            return bool(result["v"])

        return DialogService._safe_run("question_yes_cancel", title, message, _run, on_fail=False)

    @staticmethod
    def question_yes_no_cancel(
        title: str,
        message: str,
        *,
        parent: QWidget | None = None,
    ) -> DialogButton:
        """Return YES, NO, or CANCEL. Default button is Yes (matches previous QMessageBox)."""

        def _run() -> DialogButton:
            dlg = QDialog(parent)
            dlg.setWindowTitle(title)
            dlg.setModal(True)
            root = QVBoxLayout(dlg)
            lbl = QLabel(message)
            lbl.setWordWrap(True)
            root.addWidget(lbl)
            row = QHBoxLayout()
            yes_btn = QPushButton("Yes")
            no_btn = QPushButton("No")
            cancel_btn = QPushButton("Cancel")
            row.addStretch(1)
            row.addWidget(yes_btn)
            row.addWidget(no_btn)
            row.addWidget(cancel_btn)
            root.addLayout(row)

            result: dict[str, DialogButton] = {"v": DialogButton.CANCEL}

            def pick_yes() -> None:
                result["v"] = DialogButton.YES
                dlg.accept()

            def pick_no() -> None:
                result["v"] = DialogButton.NO
                dlg.accept()

            def pick_cancel() -> None:
                result["v"] = DialogButton.CANCEL
                dlg.accept()

            def on_reject_handler() -> None:
                result["v"] = DialogButton.CANCEL

            yes_btn.clicked.connect(pick_yes)
            no_btn.clicked.connect(pick_no)
            cancel_btn.clicked.connect(pick_cancel)
            dlg.rejected.connect(on_reject_handler)
            yes_btn.setDefault(True)
            dlg.exec()
            return result["v"]

        return DialogService._safe_run(
            "question_yes_no_cancel",
            title,
            message,
            _run,
            on_fail=DialogButton.CANCEL,
        )

    @staticmethod
    def two_button_choice(
        title: str,
        message: str,
        primary_label: str,
        secondary_label: str,
        *,
        parent: QWidget | None = None,
        default_primary: bool = True,
    ) -> bool:
        """Return True if *primary* button was clicked, False if *secondary*."""

        def _run() -> bool:
            dlg = QDialog(parent)
            dlg.setWindowTitle(title)
            dlg.setModal(True)
            root = QVBoxLayout(dlg)
            lbl = QLabel(message)
            lbl.setWordWrap(True)
            root.addWidget(lbl)
            row = QHBoxLayout()
            primary_btn = QPushButton(primary_label)
            secondary_btn = QPushButton(secondary_label)
            row.addStretch(1)
            row.addWidget(primary_btn)
            row.addWidget(secondary_btn)
            root.addLayout(row)

            result = {"v": False}

            def on_primary() -> None:
                result["v"] = True
                dlg.accept()

            def on_secondary() -> None:
                result["v"] = False
                dlg.accept()

            def on_reject_handler() -> None:
                result["v"] = False

            primary_btn.clicked.connect(on_primary)
            secondary_btn.clicked.connect(on_secondary)
            dlg.rejected.connect(on_reject_handler)
            if default_primary:
                primary_btn.setDefault(True)
            else:
                secondary_btn.setDefault(True)
            dlg.exec()
            return bool(result["v"])

        return DialogService._safe_run("two_button_choice", title, message, _run, on_fail=False)
