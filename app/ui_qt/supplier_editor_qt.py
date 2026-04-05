"""Add or edit a registered supplier (Qt)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from app.services.supplier_service import SupplierService

from app.ui_qt.helpers_qt import warning_message


class SupplierEditorDialogQt(QDialog):
    def __init__(self, parent, service: SupplierService, supplier_id: int | None = None):
        super().__init__(parent)
        self._service = service
        self._supplier_id = supplier_id
        self.saved = False

        self.setWindowTitle("New supplier" if supplier_id is None else "Edit supplier")
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._name = QLineEdit()
        self._phone = QLineEdit()
        self._email = QLineEdit()
        self._address = QLineEdit()
        self._notes = QLineEdit()
        form.addRow("Name *", self._name)
        form.addRow("Phone", self._phone)
        form.addRow("Email", self._email)
        form.addRow("Address", self._address)
        form.addRow("Notes", self._notes)
        root.addLayout(form)

        hint = QLabel(
            "Required name. Used to quick-fill goods receipts; each GRN still stores its own supplier snapshot."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        root.addWidget(hint)

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

        if supplier_id is not None:
            row = service.get(int(supplier_id))
            if row:
                self._name.setText(row.get("name") or "")
                self._phone.setText(row.get("phone") or "")
                self._email.setText(row.get("email") or "")
                self._address.setText(row.get("address") or "")
                self._notes.setText(row.get("notes") or "")

    def _save(self) -> None:
        try:
            if self._supplier_id is None:
                self._service.create(
                    name=self._name.text(),
                    phone=self._phone.text(),
                    email=self._email.text(),
                    address=self._address.text(),
                    notes=self._notes.text(),
                )
            else:
                self._service.update(
                    self._supplier_id,
                    name=self._name.text(),
                    phone=self._phone.text(),
                    email=self._email.text(),
                    address=self._address.text(),
                    notes=self._notes.text(),
                )
        except ValueError as e:
            warning_message(self, "Supplier", str(e))
            return
        except Exception as e:
            warning_message(self, "Supplier", str(e))
            return
        self.saved = True
        self.accept()
