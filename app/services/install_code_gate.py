"""One-time installation code on each machine (same value as Inno Setup INSTALL_CODE)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from app.config import INSTALL_CODE_REQUIRED
from app.runtime_paths import get_data_dir


def _marker_path() -> Path:
    return get_data_dir() / ".install_verified"


def is_install_verified() -> bool:
    return _marker_path().is_file()


def _write_marker() -> None:
    p = _marker_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("1", encoding="utf-8")


def ensure_first_run_install_code(parent=None) -> bool:
    """If this PC has not been verified yet, prompt once; return False if user cancels."""
    if is_install_verified():
        return True

    dlg = QDialog(parent)
    dlg.setWindowTitle("SmartStock")
    dlg.setModal(True)
    root = QVBoxLayout(dlg)
    root.addWidget(
        QLabel(
            "Enter the installation code.\n"
            "This is required once on this computer (including when using the portable folder)."
        )
    )
    edit = QLineEdit()
    edit.setPlaceholderText("Installation code")
    edit.setMinimumWidth(360)
    form = QFormLayout()
    form.addRow("Code:", edit)
    root.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    root.addWidget(buttons)

    want = (INSTALL_CODE_REQUIRED or "").strip()
    while True:
        edit.clear()
        edit.setFocus()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        got = edit.text().strip()
        if got == want:
            _write_marker()
            return True
        QMessageBox.warning(
            dlg,
            "Invalid code",
            "That code is not valid. Check with your vendor and try again.",
        )
