"""Owner user management; same AuthService calls as Tk ManageUsersDialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.auth_service import AuthService

from app.ui_qt.helpers_qt import info_message, warning_message


class ManageUsersDialogQt(QDialog):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.auth = AuthService()
        self.setWindowTitle("User accounts")
        self.resize(760, 460)

        v = QVBoxLayout(self)
        v.addWidget(
            QLabel("Each person signs in with their own username and password on the start screen.")
        )

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Username", "Full name", "Role", "Active"])
        self._tree.setColumnWidth(0, 140)
        self._tree.setColumnWidth(1, 220)
        self._tree.itemDoubleClicked.connect(lambda *_: self._edit_selected())
        v.addWidget(self._tree, 1)

        row = QHBoxLayout()
        row.addWidget(QPushButton("Add user…", clicked=self._add_user))
        row.addWidget(QPushButton("Edit…", clicked=self._edit_selected))
        row.addWidget(QPushButton("Set password…", clicked=self._set_password))
        row.addStretch(1)
        row.addWidget(QPushButton("Close", clicked=self.accept))
        v.addLayout(row)

        self._reload_table()

    def _acting(self):
        return getattr(self.main_window, "current_user", None)

    def _reload_table(self) -> None:
        self._tree.clear()
        try:
            rows = self.auth.list_users(self._acting())
        except ValueError as e:
            warning_message(self, "Users", str(e))
            self.reject()
            return
        for u in rows:
            active_txt = "Yes" if u.get("is_active") else "No"
            it = QTreeWidgetItem(
                [
                    u.get("username") or "",
                    u.get("full_name") or "",
                    (u.get("role") or "").title(),
                    active_txt,
                ]
            )
            it.setData(0, Qt.UserRole, int(u["id"]))
            self._tree.addTopLevelItem(it)

    def _selected_user_id(self) -> int | None:
        sel = self._tree.currentItem()
        if sel is None:
            warning_message(self, "Users", "Select a user in the list.")
            return None
        return int(sel.data(0, Qt.UserRole))

    def _add_user(self) -> None:
        d = QDialog(self)
        d.setWindowTitle("Add user")
        f = QFormLayout(d)
        uv = QLineEdit()
        pv = QLineEdit()
        pv.setEchoMode(QLineEdit.Password)
        nv = QLineEdit()
        rv = QComboBox()
        rv.addItems(["staff", "owner"])
        err = QLabel("")
        err.setObjectName("errorText")
        f.addRow("Username", uv)
        f.addRow("Password (min 4)", pv)
        f.addRow("Full name", nv)
        f.addRow("Role", rv)
        f.addRow(err)

        def save():
            err.setText("")
            try:
                self.auth.create_user(
                    self._acting(),
                    username=uv.text(),
                    password=pv.text(),
                    full_name=nv.text(),
                    role=rv.currentText(),
                )
            except ValueError as e:
                err.setText(str(e))
                return
            self._reload_table()
            d.accept()

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(save)
        bb.rejected.connect(d.reject)
        f.addRow(bb)
        d.exec()

    def _edit_selected(self) -> None:
        uid = self._selected_user_id()
        if uid is None:
            return
        u = self.auth.get_user(self._acting(), uid)
        if not u:
            warning_message(self, "Users", "User not found.")
            return

        d = QDialog(self)
        d.setWindowTitle(f"Edit — {u.get('username', '')}")
        f = QFormLayout(d)
        f.addRow(QLabel(f"Username: {u.get('username', '')}"))
        nv = QLineEdit(u.get("full_name") or "")
        rv = QComboBox()
        rv.addItems(["staff", "owner"])
        ix = rv.findText(str(u.get("role") or "staff").lower())
        if ix >= 0:
            rv.setCurrentIndex(ix)
        av = QCheckBox("Account active (can sign in)")
        av.setChecked(bool(u.get("is_active")))
        err = QLabel("")
        err.setObjectName("errorText")
        f.addRow("Full name", nv)
        f.addRow("Role", rv)
        f.addRow(av)
        f.addRow(err)

        def save():
            err.setText("")
            try:
                self.auth.update_user(
                    self._acting(),
                    uid,
                    full_name=nv.text(),
                    role=rv.currentText(),
                    is_active=av.isChecked(),
                )
            except ValueError as e:
                err.setText(str(e))
                return
            self._reload_table()
            d.accept()

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(save)
        bb.rejected.connect(d.reject)
        f.addRow(bb)
        d.exec()

    def _set_password(self) -> None:
        uid = self._selected_user_id()
        if uid is None:
            return
        u = self.auth.get_user(self._acting(), uid)
        if not u:
            warning_message(self, "Users", "User not found.")
            return

        d = QDialog(self)
        d.setWindowTitle(f"New password — {u.get('username', '')}")
        f = QFormLayout(d)
        p1 = QLineEdit()
        p1.setEchoMode(QLineEdit.Password)
        p2 = QLineEdit()
        p2.setEchoMode(QLineEdit.Password)
        err = QLabel("")
        err.setObjectName("errorText")
        f.addRow("New password (min 4)", p1)
        f.addRow("Confirm", p2)
        f.addRow(err)

        def save():
            err.setText("")
            if p1.text() != p2.text():
                err.setText("Passwords do not match.")
                return
            try:
                self.auth.set_password(self._acting(), uid, p1.text())
            except ValueError as e:
                err.setText(str(e))
                return
            info_message(d, "Users", "Password updated.")
            d.accept()

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(save)
        bb.rejected.connect(d.reject)
        f.addRow(bb)
        d.exec()
