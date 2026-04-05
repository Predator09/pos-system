"""Sign-in screen; pick a shop or create one (same behavior as Tk)."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QGraphicsDropShadowEffect,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import PAD_MD
from app.database.connection import db
from app.services.auth_service import AuthService
from app.services.shop_context import (
    create_new_shop,
    database_path,
    get_current_shop_id,
    list_shops,
    open_shop_database,
    shop_combo_entries,
)
from app.services.shop_settings import ShopSettings, get_display_shop_name

from app.ui_qt.helpers_qt import warning_message
from app.ui_qt.logo_widget import ShopLogoLabel


class LoginView(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._shop_combo_ids: list[str] = []
        self.auth = AuthService()
        self._has_users = self.auth.has_any_users()

        outer = QVBoxLayout(self)
        outer.addStretch(1)

        center = QWidget()
        cv = QVBoxLayout(center)
        cv.setAlignment(Qt.AlignHCenter)

        self._logo = ShopLogoLabel(center, size=96, editable=True)
        cv.addWidget(self._logo, alignment=Qt.AlignCenter)
        cv.addSpacing(PAD_MD)

        shop_pick = QWidget()
        shop_h = QHBoxLayout(shop_pick)
        shop_h.setContentsMargins(0, 0, 0, 0)
        shop_h.setSpacing(8)
        sl = QLabel("Shop")
        sl.setObjectName("muted")
        shop_h.addStretch(1)
        shop_h.addWidget(sl)
        self._shop_combo = QComboBox()
        self._shop_combo.setMinimumWidth(220)
        self._shop_combo.setFocusPolicy(Qt.StrongFocus)
        self._shop_combo.currentIndexChanged.connect(self._on_shop_index_changed)
        shop_h.addWidget(self._shop_combo)
        new_shop_btn = QPushButton("New shop…")
        new_shop_btn.setObjectName("ghost")
        new_shop_btn.setCursor(Qt.PointingHandCursor)
        new_shop_btn.clicked.connect(self._on_new_shop)
        shop_h.addWidget(new_shop_btn)
        shop_h.addStretch(1)
        cv.addWidget(shop_pick, alignment=Qt.AlignCenter)
        cv.addSpacing(PAD_MD // 2)

        bn_lbl = QLabel("Business name")
        bn_lbl.setObjectName("muted")
        bn_lbl.setAlignment(Qt.AlignCenter)
        cv.addWidget(bn_lbl)

        shop_row = QWidget()
        shop_h = QHBoxLayout(shop_row)
        shop_h.setContentsMargins(0, 0, 0, 0)
        shop_h.setSpacing(8)
        self._shop_entry = QLineEdit()
        self._shop_entry.setMinimumWidth(240)
        self._shop_entry.setText(get_display_shop_name())
        tf = QFont()
        tf.setPointSize(16)
        tf.setBold(True)
        self._shop_entry.setFont(tf)
        shop_h.addStretch(1)
        shop_h.addWidget(self._shop_entry, alignment=Qt.AlignCenter)
        save_shop = QPushButton("Save")
        save_shop.setObjectName("ghost")
        save_shop.setCursor(Qt.PointingHandCursor)
        save_shop.clicked.connect(self._save_business_name)
        shop_h.addWidget(save_shop)
        shop_h.addStretch(1)
        cv.addWidget(shop_row, alignment=Qt.AlignCenter)

        self._stack = QStackedWidget()
        self._stack.setMinimumWidth(320)

        # --- Page 0: Sign in ---
        sign_wrap = QWidget()
        sign_outer = QVBoxLayout(sign_wrap)
        sign_outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("loginCard")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(56)
        shadow.setColor(QColor(0, 0, 0, 72))
        shadow.setOffset(0, 14)
        card.setGraphicsEffect(shadow)
        gl = QGridLayout(card)
        gl.setContentsMargins(28, 24, 28, 24)
        gl.setHorizontalSpacing(12)
        gl.setVerticalSpacing(10)

        sign_hdr = QLabel("Sign in")
        sign_hdr.setObjectName("section")
        gl.addWidget(sign_hdr, 0, 0, 1, 2)
        gl.addWidget(QLabel("Username"), 1, 0, 1, 2)
        self._user_entry = QLineEdit()
        self._user_entry.setText("admin" if self._has_users else "")
        self._user_entry.setMinimumWidth(280)
        gl.addWidget(self._user_entry, 2, 0, 1, 2)
        gl.addWidget(QLabel("Password"), 3, 0, 1, 2)
        self._pass_entry = QLineEdit()
        self._pass_entry.setEchoMode(QLineEdit.Password)
        self._pass_entry.setMinimumWidth(280)
        gl.addWidget(self._pass_entry, 4, 0, 1, 2)

        self._error = QLabel("")
        self._error.setObjectName("errorText")
        self._error.setWordWrap(True)
        gl.addWidget(self._error, 5, 0, 1, 2)

        sign_btn = QPushButton("Sign in")
        sign_btn.setObjectName("primary")
        sign_btn.setCursor(Qt.PointingHandCursor)
        sign_btn.clicked.connect(self._try_login)
        gl.addWidget(sign_btn, 6, 0, 1, 2)

        sign_outer.addWidget(card)
        self._stack.addWidget(sign_wrap)

        # --- Page 1: Register ---
        up_wrap = QWidget()
        up_outer = QVBoxLayout(up_wrap)
        up_outer.setContentsMargins(0, 0, 0, 0)
        up_card = QFrame()
        up_card.setObjectName("loginCard")
        us = QGraphicsDropShadowEffect(up_card)
        us.setBlurRadius(56)
        us.setColor(QColor(0, 0, 0, 72))
        us.setOffset(0, 14)
        up_card.setGraphicsEffect(us)
        ug = QGridLayout(up_card)
        ug.setContentsMargins(28, 24, 28, 24)
        ug.setHorizontalSpacing(12)
        ug.setVerticalSpacing(10)

        r = 0
        uh = QLabel("Add new shop")
        uh.setObjectName("section")
        ug.addWidget(uh, r, 0, 1, 2)
        r += 1
        hint = QLabel(
            "Your business name above will be used for receipts and the app. You will be the owner."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        ug.addWidget(hint, r, 0, 1, 2)
        r += 1

        ug.addWidget(QLabel("Your full name"), r, 0, 1, 2)
        r += 1
        self._reg_full = QLineEdit()
        self._reg_full.setMinimumWidth(280)
        ug.addWidget(self._reg_full, r, 0, 1, 2)
        r += 1
        ug.addWidget(QLabel("Username"), r, 0, 1, 2)
        r += 1
        self._reg_user = QLineEdit()
        self._reg_user.setMinimumWidth(280)
        ug.addWidget(self._reg_user, r, 0, 1, 2)
        r += 1
        ug.addWidget(QLabel("Password"), r, 0, 1, 2)
        r += 1
        self._reg_pass = QLineEdit()
        self._reg_pass.setEchoMode(QLineEdit.Password)
        self._reg_pass.setMinimumWidth(280)
        ug.addWidget(self._reg_pass, r, 0, 1, 2)
        r += 1
        ug.addWidget(QLabel("Confirm password"), r, 0, 1, 2)
        r += 1
        self._reg_confirm = QLineEdit()
        self._reg_confirm.setEchoMode(QLineEdit.Password)
        self._reg_confirm.setMinimumWidth(280)
        ug.addWidget(self._reg_confirm, r, 0, 1, 2)
        r += 1

        self._reg_error = QLabel("")
        self._reg_error.setObjectName("errorText")
        self._reg_error.setWordWrap(True)
        ug.addWidget(self._reg_error, r, 0, 1, 2)
        r += 1

        create_btn = QPushButton("Create shop & sign in")
        create_btn.setObjectName("primary")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.clicked.connect(self._try_register)
        ug.addWidget(create_btn, r, 0, 1, 2)
        r += 1
        back_btn = QPushButton("Back to sign in")
        back_btn.setObjectName("ghost")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self._show_signin)
        ug.addWidget(back_btn, r, 0, 1, 2)

        up_outer.addWidget(up_card)
        self._stack.addWidget(up_wrap)

        cv.addSpacing(PAD_MD * 2)
        cv.addWidget(self._stack, alignment=Qt.AlignCenter)

        hint2 = QLabel(
            "Hello 👋 How's your day? Hope it's a good one! ☀️\n\n"
            "Set your business name above — it's saved for receipts and the app. "
            "Tap the circle for your logo (right-click to remove). ✨"
        )
        hint2.setObjectName("muted")
        hint2.setWordWrap(True)
        hint2.setMaximumWidth(400)
        hint2.setAlignment(Qt.AlignCenter)
        cv.addWidget(hint2, alignment=Qt.AlignCenter)

        outer.addWidget(center, alignment=Qt.AlignCenter)
        outer.addStretch(1)

        self._user_entry.returnPressed.connect(self._pass_entry.setFocus)
        self._pass_entry.returnPressed.connect(self._try_login)
        self._reg_full.returnPressed.connect(self._reg_user.setFocus)
        self._reg_user.returnPressed.connect(self._reg_pass.setFocus)
        self._reg_pass.returnPressed.connect(self._reg_confirm.setFocus)
        self._reg_confirm.returnPressed.connect(self._try_register)

        self._populate_shop_combo()
        self._refresh_after_shop_change()

    def _populate_shop_combo(self, select_id: str | None = None) -> None:
        shops = list_shops()
        labels, ids = shop_combo_entries(shops)
        self._shop_combo_ids = ids
        self._shop_combo.blockSignals(True)
        self._shop_combo.clear()
        for lab in labels:
            self._shop_combo.addItem(lab)
        want = select_id if select_id is not None else get_current_shop_id()
        if want in ids:
            self._shop_combo.setCurrentIndex(ids.index(want))
        elif self._shop_combo.count() > 0:
            self._shop_combo.setCurrentIndex(0)
        self._shop_combo.blockSignals(False)

    def _on_shop_index_changed(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._shop_combo_ids):
            return
        sid = self._shop_combo_ids[idx]
        if sid == get_current_shop_id():
            return
        try:
            open_shop_database(db, sid)
        except Exception as e:
            warning_message(self.window(), "Switch shop", str(e))
            self._populate_shop_combo()
            return
        self._refresh_after_shop_change()

    def _on_new_shop(self) -> None:
        text, ok = QInputDialog.getText(self.window(), "New shop", "Business / shop name:")
        if not ok:
            return
        name = (text or "").strip()
        if not name:
            return
        try:
            sid = create_new_shop(name)
            open_shop_database(db, sid)
        except Exception as e:
            warning_message(self.window(), "New shop", str(e))
            return
        self._populate_shop_combo(select_id=sid)
        self._refresh_after_shop_change()

    def _refresh_after_shop_change(self) -> None:
        self.auth = AuthService()
        self._has_users = self.auth.has_any_users()
        self._error.setText("")
        self._reg_error.setText("")
        self._shop_entry.setText(get_display_shop_name())
        self._logo.refresh()
        self._user_entry.setText("admin" if self._has_users else "")
        if not self._has_users:
            self._stack.setCurrentIndex(1)
            self._reg_full.setFocus()
        else:
            self._stack.setCurrentIndex(0)
            self._pass_entry.setFocus()

    def _show_signin(self) -> None:
        self._reg_error.setText("")
        self._stack.setCurrentIndex(0)
        self._pass_entry.setFocus()

    def showEvent(self, event):
        super().showEvent(event)
        self._logo.refresh()
        self._shop_entry.setText(get_display_shop_name())
        self._populate_shop_combo()
        if not getattr(self, "_did_entrance_fade", False):
            self._did_entrance_fade = True
            from app.ui_qt.motion_qt import fade_in_widget

            fade_in_widget(self, 260)

    def _save_business_name(self) -> None:
        name = (self._shop_entry.text() or "").strip()
        if not name:
            warning_message(self.window(), "Business name", "Enter a business name.")
            return
        try:
            ShopSettings().set_shop_name(name)
        except ValueError as e:
            warning_message(self.window(), "Business name", str(e))

    def _try_register(self) -> None:
        self._reg_error.setText("")
        shop = (self._shop_entry.text() or "").strip()
        full = (self._reg_full.text() or "").strip()
        uname = (self._reg_user.text() or "").strip()
        p1 = (self._reg_pass.text() or "").replace("\r", "").replace("\n", "")
        p2 = (self._reg_confirm.text() or "").replace("\r", "").replace("\n", "")

        if p1 != p2:
            self._reg_error.setText("Passwords do not match.")
            return

        try:
            user = self.auth.register_new_shop(
                shop_name=shop,
                full_name=full,
                username=uname,
                password=p1,
            )
        except ValueError as e:
            self._reg_error.setText(str(e))
            return
        except Exception as e:
            self._reg_error.setText(f"Could not register: {e}")
            return

        self._shop_entry.setText(get_display_shop_name())
        self._reg_pass.clear()
        self._reg_confirm.clear()
        self._main.enter_app(user)

    def _try_login(self) -> None:
        self._error.setText("")
        uname = (self._user_entry.text() or "").strip()
        pwd = (self._pass_entry.text() or "").replace("\r", "").replace("\n", "")

        if not uname:
            self._error.setText("Enter your username.")
            return

        self.auth.ensure_default_users()

        try:
            user = self.auth.authenticate(uname, pwd)
        except Exception as e:
            self._error.setText(f"Sign-in error: {e}")
            return

        if user:
            self._pass_entry.clear()
            self._main.enter_app(user)
            return

        try:
            tbl = db.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if tbl is None:
                self._error.setText(
                    f"Users table missing. Delete {database_path()} and restart (resets this shop only)."
                )
                return

            exists = db.fetchone(
                "SELECT 1 FROM users WHERE lower(username) = lower(?) AND is_active = 1",
                (uname,),
            )
            if exists is None:
                self._error.setText(
                    f'No active account found for "{uname}". Check the username or ask your store owner.'
                )
            else:
                self._error.setText("Wrong password. Try again or use the correct account password.")
        except sqlite3.OperationalError as e:
            self._error.setText(f"Database error: {e}")
