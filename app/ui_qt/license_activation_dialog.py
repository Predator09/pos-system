"""Qt dialog to activate SmartStock by loading a license.json file."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.services.dialog_service import DialogService
from app.services.license_service import LicenseService


class LicenseActivationDialog(QDialog):
    def __init__(self, parent=None, *, initial_reason: str = "", renewal_mode: bool = False) -> None:
        super().__init__(parent)
        self._renewal_mode = renewal_mode
        self.setWindowTitle("Renew license" if renewal_mode else "License activation")
        self.setModal(True)
        self.resize(560, 220)

        self._service = LicenseService()
        self._initial_reason = (initial_reason or "").strip()
        self._status_label: QLabel | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        if self._renewal_mode:
            title = QLabel("Subscription / license renewal")
            title.setStyleSheet("font-size: 15px; font-weight: 700;")
            root.addWidget(title)
            hint = (
                self._initial_reason
                or "Load an updated license.json for this device. You can renew before expiry."
            )
            reason_lbl = QLabel(hint)
            reason_lbl.setWordWrap(True)
            root.addWidget(reason_lbl)
        else:
            title = QLabel("SmartStock license is required")
            title.setStyleSheet("font-size: 15px; font-weight: 700;")
            root.addWidget(title)

            reason = self._initial_reason or "No valid license was found."
            reason_lbl = QLabel(f"Reason: {reason}")
            reason_lbl.setWordWrap(True)
            root.addWidget(reason_lbl)

        dev = self._service.current_device_id()
        dev_lbl = QLabel(f"Device ID: {dev}")
        dev_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        dev_lbl.setWordWrap(True)
        root.addWidget(dev_lbl)

        self._status_label = QLabel(
            "Choose a license.json file for this device."
            if self._renewal_mode
            else "Load a license.json file for this device."
        )
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        row = QHBoxLayout()
        row.addStretch(1)
        load_btn = QPushButton("Load License File")
        load_btn.clicked.connect(self._on_load_license_file)
        row.addWidget(load_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(cancel_btn)
        root.addLayout(row)

    def _on_load_license_file(self) -> None:
        if not self._renewal_mode:
            current = self._service.validate_license()
            if bool(current.get("valid")):
                msg = "License is already activated on this device."
                if self._status_label is not None:
                    self._status_label.setText(msg)
                DialogService.info("License already active", msg, parent=self)
                self.reject()
                return

        chosen, _ = QFileDialog.getOpenFileName(
            self,
            "Select license.json",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if not chosen:
            return

        result = self._service.validate_license_file(chosen)
        if not bool(result.get("valid")):
            reason = str(result.get("reason") or "License validation failed")
            if self._status_label is not None:
                self._status_label.setText(f"Validation failed: {reason}")
            DialogService.error("Invalid license", reason, parent=self)
            return

        try:
            if self._renewal_mode:
                self._service.replace_license_from_file(chosen)
            else:
                self._service.activate_from_file(chosen)
        except Exception as exc:
            msg = f"Could not save license file: {exc}"
            if self._status_label is not None:
                self._status_label.setText(msg)
            DialogService.error("Activation failed", msg, parent=self)
            return

        self.accept()

