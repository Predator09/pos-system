"""Installation code gate: first run and periodic re-verification (same secret as Inno Setup)."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from app.config import (
    INSTALL_CODE_REQUIRED,
    INSTALL_CODE_REQUIRED_SHA256,
    INSTALL_CODE_REVERIFY_INTERVAL_DAYS,
)
from app.runtime_paths import get_data_dir


def _marker_path() -> Path:
    return get_data_dir() / ".install_verified"


def _code_is_valid(got: str) -> bool:
    value = (got or "").strip()
    expected_hash = (INSTALL_CODE_REQUIRED_SHA256 or "").strip().lower()
    if expected_hash:
        got_hash = hashlib.sha256(value.encode("utf-8")).hexdigest().lower()
        return hmac.compare_digest(got_hash, expected_hash)
    expected = (INSTALL_CODE_REQUIRED or "").strip()
    return hmac.compare_digest(value, expected)


def _read_last_verified_utc() -> datetime | None:
    """Return last successful verification time, or None if never verified."""
    p = _marker_path()
    if not p.is_file():
        return None
    raw = p.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "verified_at" in data:
            s = data["verified_at"]
            if isinstance(s, str):
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    # Legacy: file contained plain "1" (or unreadable content) — treat file mtime as verification time.
    try:
        return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def _write_verified_at(when: datetime) -> None:
    p = _marker_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    utc = when.astimezone(timezone.utc)
    payload = {"verified_at": utc.isoformat()}
    p.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def _needs_reverification(last: datetime | None) -> bool:
    if last is None:
        return True
    now = datetime.now(timezone.utc)
    return now - last >= timedelta(days=INSTALL_CODE_REVERIFY_INTERVAL_DAYS)


def _prompt_install_code(
    parent,
    reason: Literal["first", "reverify"],
) -> bool:
    dlg = QDialog(parent)
    dlg.setWindowTitle("SmartStock")
    dlg.setModal(True)
    root = QVBoxLayout(dlg)

    if reason == "first":
        intro = (
            "Enter the installation code.\n"
            "This is required once on this computer (including when using the portable folder)."
        )
    else:
        intro = (
            f"It has been {INSTALL_CODE_REVERIFY_INTERVAL_DAYS} days since the last verification.\n"
            "Enter your installation code to continue using SmartStock."
        )
    root.addWidget(QLabel(intro))

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

    while True:
        edit.clear()
        edit.setFocus()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        got = edit.text().strip()
        if _code_is_valid(got):
            _write_verified_at(datetime.now(timezone.utc))
            return True
        QMessageBox.warning(
            dlg,
            "Invalid code",
            "That code is not valid. Check with your vendor and try again.",
        )


def ensure_install_code(parent=None) -> bool:
    """
    Block startup until the install code is accepted (first run or after the re-verification interval).
    Returns False if the user cancels.
    """
    last = _read_last_verified_utc()
    if not _needs_reverification(last):
        return True
    reason: Literal["first", "reverify"] = "first" if last is None else "reverify"
    return _prompt_install_code(parent, reason)


def ensure_first_run_install_code(parent=None) -> bool:
    """Backward-compatible name for :func:`ensure_install_code`."""
    return ensure_install_code(parent)
