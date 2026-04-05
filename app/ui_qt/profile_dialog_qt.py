"""Qt: signed-in user profile — name, username, optional password change."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from app.services.auth_service import AuthService


class ProfileDialogQt(QDialog):
    def __init__(self, parent, main_window) -> None:
        super().__init__(parent)
        self._main = main_window
        self._auth = AuthService()
        self.setWindowTitle("My profile")
        self.setModal(True)
        self.resize(440, 420)

        u = getattr(main_window, "current_user", None) or {}
        self._user_id = u.get("id")

        root = QVBoxLayout(self)
        hint = QLabel(
            "Update your display name and username. To change password, fill all three password fields."
        )
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        root.addWidget(hint)

        form = QFormLayout()
        self._full = QLineEdit((u.get("full_name") or "").strip())
        self._user = QLineEdit((u.get("username") or "").strip())
        form.addRow("Full name", self._full)
        form.addRow("Username", self._user)

        pw_label = QLabel("<b>Change password (optional)</b>")
        form.addRow(pw_label)
        self._cur = QLineEdit()
        self._cur.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Current password", self._cur)
        self._new = QLineEdit()
        self._new.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("New password", self._new)
        self._conf = QLineEdit()
        self._conf.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Confirm new password", self._conf)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _save(self) -> None:
        if self._user_id is None:
            QMessageBox.warning(self, "My profile", "Not signed in.")
            return

        cur = (self._cur.text() or "").replace("\r", "").replace("\n", "")
        new = (self._new.text() or "").replace("\r", "").replace("\n", "")
        conf = (self._conf.text() or "").replace("\r", "").replace("\n", "")
        any_pw = bool(cur or new or conf)
        if any_pw:
            if not cur or not new or not conf:
                QMessageBox.warning(
                    self,
                    "My profile",
                    "To change password, fill current, new, and confirm.",
                )
                return
            if new != conf:
                QMessageBox.warning(self, "My profile", "New password and confirmation do not match.")
                return
            if len(new.strip()) < 4:
                QMessageBox.warning(self, "My profile", "New password must be at least 4 characters.")
                return

        acting = getattr(self._main, "current_user", None)
        try:
            snap = self._auth.update_own_profile(
                acting,
                full_name=self._full.text(),
                username=self._user.text(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "My profile", str(e))
            return

        self._main.current_user = snap
        if hasattr(self._main, "_sync_user_widgets"):
            self._main._sync_user_widgets()

        if any_pw:
            try:
                self._auth.change_own_password(snap, cur, new)
            except ValueError as e:
                QMessageBox.warning(self, "My profile", str(e))
                return
            self._cur.clear()
            self._new.clear()
            self._conf.clear()

        QMessageBox.information(self, "My profile", "Profile saved.")
        self.accept()

