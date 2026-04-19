"""Qt: signed-in user profile — name, username, optional password change; owners can delete a shop."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.database.connection import db
from app.services.auth_service import AuthService
from app.services.shop_context import delete_shop, list_shops, shop_combo_entries
from app.ui_qt.icon_utils import set_button_icon, style_dialog_button_box


class ProfileDialogQt(QDialog):
    def __init__(self, parent, main_window) -> None:
        super().__init__(parent)
        self._main = main_window
        self._auth = AuthService()
        self.setWindowTitle("My profile")
        self.setModal(True)
        self.resize(480, 520)

        u = getattr(main_window, "current_user", None) or {}
        self._user_id = u.get("id")
        self._shop_combo: QComboBox | None = None
        self._shop_ids: list[str] = []
        self._shop_warn: QLabel | None = None

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

        if AuthService.is_owner(u):
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setFrameShadow(QFrame.Shadow.Plain)
            sep.setObjectName("loginFormSeparator")
            sep.setFixedHeight(1)
            form.addRow(sep)

            admin_hdr = QLabel("<b>Shop administration (owners)</b>")
            admin_hdr.setWordWrap(True)
            form.addRow(admin_hdr)

            admin_hint = QLabel(
                "Delete a shop permanently (database, sales, products, backups, receipts, images). "
                "Requires at least two shops."
            )
            admin_hint.setWordWrap(True)
            admin_hint.setObjectName("muted")
            form.addRow(admin_hint)

            self._shop_combo = QComboBox()
            self._shop_combo.setMinimumWidth(320)
            form.addRow("Shop to remove", self._shop_combo)

            self._shop_warn = QLabel("")
            self._shop_warn.setWordWrap(True)
            self._shop_warn.setObjectName("errorText")
            form.addRow(self._shop_warn)

            del_btn = QPushButton("Delete selected shop…")
            del_btn.setObjectName("ghost")
            del_btn.clicked.connect(self._on_delete_shop)
            set_button_icon(del_btn, "fa5s.trash-alt")
            form.addRow("", del_btn)

            self._reload_shop_list()

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        style_dialog_button_box(buttons, ok_icon="fa5s.save")
        root.addWidget(buttons)

    def _reload_shop_list(self) -> None:
        if self._shop_combo is None:
            return
        self._shop_combo.blockSignals(True)
        self._shop_combo.clear()
        shops = list_shops()
        labels, ids = shop_combo_entries(shops)
        self._shop_ids = ids
        for lab in labels:
            self._shop_combo.addItem(lab)
        self._shop_combo.blockSignals(False)
        if self._shop_warn is not None:
            if len(shops) < 2:
                self._shop_warn.setText(
                    "Add another shop (sign out → New shop…) before you can delete one."
                )
            else:
                self._shop_warn.setText("")

    def _on_delete_shop(self) -> None:
        if not AuthService.is_owner(getattr(self._main, "current_user", None)):
            QMessageBox.warning(self, "My profile", "Only an owner can delete a shop.")
            return
        if self._shop_combo is None:
            return

        shops = list_shops()
        if len(shops) < 2:
            QMessageBox.warning(
                self,
                "My profile",
                "You cannot delete the only shop. Create another shop first (sign out → New shop…).",
            )
            return

        idx = self._shop_combo.currentIndex()
        if idx < 0 or idx >= len(self._shop_ids):
            return
        shop_id = self._shop_ids[idx]
        shop_name = self._shop_combo.currentText()

        q1 = QMessageBox.question(
            self,
            "Delete shop",
            f"Permanently delete “{shop_name}” and all of its data?\n\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if q1 != QMessageBox.StandardButton.Yes:
            return

        q2 = QMessageBox.question(
            self,
            "Confirm deletion",
            f'Click Yes only if you are sure you want to erase “{shop_name}”.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if q2 != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_shop(shop_id, db)
        except ValueError as e:
            QMessageBox.warning(self, "My profile", str(e))
            return
        except OSError as e:
            QMessageBox.warning(
                self,
                "My profile",
                f"Could not remove shop files (they may be in use):\n{e}",
            )
            return

        if hasattr(self._main, "refresh_shop_context_ui"):
            self._main.refresh_shop_context_ui()

        self._reload_shop_list()
        QMessageBox.information(
            self,
            "My profile",
            "The shop was removed. You are now working in the remaining shop.",
        )

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
