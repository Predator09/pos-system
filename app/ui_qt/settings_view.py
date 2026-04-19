"""Central Settings: appearance, shop branding, receipt printing, backup, users."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app import config as app_config
from app.config import PAD_MD
from app.services.app_settings import AppSettings
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService
from app.services.shop_settings import ShopSettings, get_display_shop_name
from app.ui_qt.helpers_qt import info_message, warning_message
from app.ui_qt.icon_utils import set_button_icon
from app.ui_qt.logo_widget import ShopLogoLabel
from app.ui_qt.manage_users_qt import ManageUsersDialogQt


class SettingsView(QWidget):
    """Tabbed preferences aligned with how shops actually run the register."""

    def __init__(self, main_window, parent=None) -> None:
        super().__init__(parent)
        self._main = main_window
        self._backup = BackupService()
        self._shop = ShopSettings()
        self._suppress_appearance = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(PAD_MD)

        intro = QLabel(
            "Tune appearance, branding, receipt printing, backups, and team access. "
            "Changes apply to this device; shop data stays local."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        root.addWidget(intro)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setTabPosition(QTabWidget.North)
        self._tabs.addTab(self._build_general_tab(), "General")
        self._tabs.addTab(self._build_shop_tab(), "Shop")
        self._tabs.addTab(self._build_receipts_tab(), "Receipts & printing")
        self._tabs.addTab(self._build_data_tab(), "Data & backup")
        self._tabs.addTab(self._build_team_tab(), "Team")
        root.addWidget(self._tabs, 1)

    def _wrap_scroll(self, inner: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        return scroll

    def _build_general_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(PAD_MD)

        appearance = QGroupBox("Appearance")
        al = QVBoxLayout(appearance)
        row = QHBoxLayout()
        row.addWidget(QLabel("Dark mode"))
        self._appearance_check = QCheckBox()
        self._appearance_check.toggled.connect(self._on_appearance_toggle)
        row.addWidget(self._appearance_check)
        row.addStretch(1)
        al.addLayout(row)
        hint = QLabel("Matches the dashboard toggle; use whichever you prefer.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        al.addWidget(hint)
        v.addWidget(appearance)

        about = QGroupBox("About")
        bl = QVBoxLayout(about)
        bl.addWidget(QLabel(f"{app_config.APP_NAME} · version {app_config.VERSION}"))
        self._about_footer = QLabel()
        self._about_footer.setObjectName("muted")
        self._about_footer.setWordWrap(True)
        bl.addWidget(self._about_footer)
        v.addWidget(about)

        v.addStretch(1)
        return self._wrap_scroll(page)

    def _build_shop_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(PAD_MD)

        box = QGroupBox("Business profile")
        gl = QVBoxLayout(box)

        form = QFormLayout()
        self._shop_name_edit = QLineEdit()
        self._shop_name_edit.setPlaceholderText("Name shown on receipts and in the app")
        self._shop_name_edit.setMinimumWidth(320)
        form.addRow("Business name", self._shop_name_edit)

        self._biz_phone = QLineEdit()
        self._biz_phone.setPlaceholderText("Phone — optional, shown on receipts")
        self._biz_phone.setMinimumWidth(320)
        form.addRow("Phone", self._biz_phone)

        self._biz_email = QLineEdit()
        self._biz_email.setPlaceholderText("Email — optional, shown on receipts")
        self._biz_email.setMinimumWidth(320)
        form.addRow("Email", self._biz_email)

        self._biz_address = QPlainTextEdit()
        self._biz_address.setPlaceholderText("Address — optional; line breaks are kept on receipts")
        self._biz_address.setFixedHeight(76)
        form.addRow("Address", self._biz_address)

        logo_row = QHBoxLayout()
        self._shop_logo = ShopLogoLabel(self, size=64, editable=False)
        logo_btns = QVBoxLayout()
        choose = QPushButton("Choose logo…", clicked=self._on_choose_logo)
        set_button_icon(choose, "fa5s.image")
        remove = QPushButton("Remove logo", clicked=self._on_remove_logo)
        remove.setObjectName("ghost")
        set_button_icon(remove, "fa5s.times")
        logo_btns.addWidget(choose)
        logo_btns.addWidget(remove)
        logo_btns.addStretch(1)
        logo_row.addWidget(self._shop_logo)
        logo_row.addLayout(logo_btns, 1)
        gl.addLayout(form)
        gl.addLayout(logo_row)

        cap = QLabel(
            "Phone, email, and address print on customer receipts, PDF copies, and period summaries. "
            "Logo appears on receipts (PDF), the sidebar, and sale dialogs. PNG or JPG recommended."
        )
        cap.setObjectName("muted")
        cap.setWordWrap(True)
        gl.addWidget(cap)

        save_shop = QPushButton("Save business profile", clicked=self._on_save_shop_profile)
        save_shop.setObjectName("primary")
        set_button_icon(save_shop, "fa5s.save")
        gl.addWidget(save_shop)

        v.addWidget(box)
        v.addStretch(1)
        return self._wrap_scroll(page)

    def _build_receipts_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(PAD_MD)

        box = QGroupBox("Receipt printer")
        gl = QVBoxLayout(box)

        expl = QLabel(
            "By default, receipts print through the operating system (PDF with logo when possible, "
            "otherwise plain text). For a thermal or label printer, set a command that reads "
            "UTF-8 receipt text from standard input — for example a small helper that sends raw text "
            "or ESC/POS to your device."
        )
        expl.setObjectName("muted")
        expl.setWordWrap(True)
        gl.addWidget(expl)

        self._receipt_status = QLabel()
        self._receipt_status.setWordWrap(True)
        gl.addWidget(self._receipt_status)

        self._receipt_cmd_edit = QPlainTextEdit()
        self._receipt_cmd_edit.setPlaceholderText(
            "Example: C:\\Tools\\receiptpipe.exe   (executable must accept stdin; no shell metacharacters)"
        )
        self._receipt_cmd_edit.setFixedHeight(88)
        gl.addWidget(QLabel("Custom command (optional)"))
        gl.addWidget(self._receipt_cmd_edit)

        row = QHBoxLayout()
        save_r = QPushButton("Save print command", clicked=self._on_save_receipt_cmd)
        save_r.setObjectName("primary")
        set_button_icon(save_r, "fa5s.save")
        reset_r = QPushButton("Use installation default", clicked=self._on_reset_receipt_cmd)
        reset_r.setObjectName("ghost")
        set_button_icon(reset_r, "fa5s.undo")
        row.addWidget(save_r)
        row.addWidget(reset_r)
        row.addStretch(1)
        gl.addLayout(row)

        v.addWidget(box)
        v.addStretch(1)
        return self._wrap_scroll(page)

    def _build_data_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(PAD_MD)

        box = QGroupBox("Backups")
        gl = QVBoxLayout(box)
        self._backup_status = QLabel()
        self._backup_status.setWordWrap(True)
        gl.addWidget(self._backup_status)

        row = QHBoxLayout()
        go = QPushButton("Backup now", clicked=self._on_backup_now)
        go.setObjectName("primary")
        set_button_icon(go, "fa5s.database")
        folder = QPushButton("Open backup folder", clicked=self._on_open_backup_folder)
        set_button_icon(folder, "fa5s.folder-open")
        row.addWidget(go)
        row.addWidget(folder)
        row.addStretch(1)
        gl.addLayout(row)

        note = QLabel(
            "JSON backups include products, sales, and purchases for this shop database. "
            "Keep copies somewhere safe if you replace this computer."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        gl.addWidget(note)

        v.addWidget(box)
        v.addStretch(1)
        return self._wrap_scroll(page)

    def _build_team_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(PAD_MD)

        box = QGroupBox("User accounts")
        gl = QVBoxLayout(box)
        self._team_hint = QLabel()
        self._team_hint.setWordWrap(True)
        gl.addWidget(self._team_hint)

        self._manage_users_btn = QPushButton("Manage users…", clicked=self._on_manage_users)
        set_button_icon(self._manage_users_btn, "fa5s.users-cog")
        gl.addWidget(self._manage_users_btn)

        v.addWidget(box)
        v.addStretch(1)
        return self._wrap_scroll(page)

    def _sync_receipt_ui(self) -> None:
        app_s = AppSettings()
        o = app_s.receipt_print_command_override()
        if o is not None:
            self._receipt_cmd_edit.setPlainText(o)
        else:
            self._receipt_cmd_edit.clear()
        eff = app_s.get_receipt_print_command()
        if eff:
            self._receipt_status.setText(
                "Active: custom print command — UTF-8 receipt text is sent on standard input."
            )
        else:
            self._receipt_status.setText(
                "Active: system print queue — PDF with logo when possible, otherwise plain text."
            )

    def _on_save_receipt_cmd(self) -> None:
        raw = self._receipt_cmd_edit.toPlainText().strip()
        AppSettings().set_receipt_print_command_override(raw)
        self._sync_receipt_ui()
        info_message(self.window(), "Receipt printing", "Print command saved for this device.")

    def _on_reset_receipt_cmd(self) -> None:
        AppSettings().set_receipt_print_command_override(None)
        self._sync_receipt_ui()
        info_message(
            self.window(),
            "Receipt printing",
            "Cleared this device’s override. The app uses `RECEIPT_PRINT_COMMAND` from `app/config.py` if set, "
            "otherwise the system print dialog.",
        )

    def _on_appearance_toggle(self, checked: bool) -> None:
        if self._suppress_appearance:
            return
        mode = "dark" if checked else "light"
        mw = self._main
        if hasattr(mw, "apply_appearance"):
            if not mw.apply_appearance(mode):
                warning_message(self.window(), "Theme", "Could not switch appearance.")
                self.sync_appearance_switch()

    def sync_appearance_switch(self) -> None:
        """Keep the dark-mode checkbox in sync (e.g. after changing theme from the dashboard)."""
        dark = AppSettings().get_appearance() == "dark"
        self._suppress_appearance = True
        try:
            self._appearance_check.setChecked(dark)
        finally:
            self._suppress_appearance = False

    def _on_choose_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose shop logo",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp);;All (*.*)",
        )
        if not path:
            return
        try:
            self._shop.set_logo_from_file(path)
            self._shop_logo.refresh()
            if hasattr(self._main, "refresh_shop_context_ui"):
                self._main.refresh_shop_context_ui()
        except Exception as e:
            warning_message(self.window(), "Logo", str(e))

    def _on_remove_logo(self) -> None:
        self._shop.clear_logo()
        self._shop_logo.refresh()
        if hasattr(self._main, "refresh_shop_context_ui"):
            self._main.refresh_shop_context_ui()

    def _on_save_shop_profile(self) -> None:
        try:
            self._shop.set_shop_name(self._shop_name_edit.text())
        except ValueError as e:
            warning_message(self.window(), "Business profile", str(e))
            return
        self._shop.set_business_phone(self._biz_phone.text())
        self._shop.set_business_email(self._biz_email.text())
        self._shop.set_business_address(self._biz_address.toPlainText())
        if hasattr(self._main, "refresh_shop_context_ui"):
            self._main.refresh_shop_context_ui()
        info_message(self.window(), "Business profile", "Saved.")

    def _on_backup_now(self) -> None:
        try:
            path = self._backup.create_full_backup()
            self._sync_backup_status()
            info_message(self.window(), "Backup complete", f"Backup saved to:\n{path}")
        except Exception as e:
            warning_message(self.window(), "Backup error", str(e))

    def _on_open_backup_folder(self) -> None:
        p = self._backup.backup_dir.resolve()
        p.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(p))):
            warning_message(self.window(), "Folder", f"Could not open:\n{p}")

    def _sync_backup_status(self) -> None:
        self._backup_status.setText(self._backup.latest_backup_summary())

    def _on_manage_users(self) -> None:
        if not AuthService.is_owner(getattr(self._main, "current_user", None)):
            return
        ManageUsersDialogQt(self.window(), self._main).exec()

    def _sync_team_tab(self) -> None:
        owner = AuthService.is_owner(getattr(self._main, "current_user", None))
        self._manage_users_btn.setVisible(owner)
        if owner:
            self._team_hint.setObjectName("")
            self._team_hint.setText(
                "Create staff logins, reset passwords, and control who can sign in to this shop."
            )
        else:
            self._team_hint.setObjectName("muted")
            self._team_hint.setText(
                "Only the shop owner can add or edit user accounts. Ask an owner to use Manage users."
            )

    def refresh(self) -> None:
        self._shop_name_edit.setText(get_display_shop_name())
        self._biz_phone.setText(self._shop.get_business_phone())
        self._biz_email.setText(self._shop.get_business_email())
        self._biz_address.setPlainText(self._shop.get_business_address())
        self._shop_logo.refresh()
        self.sync_appearance_switch()
        from app.config import format_app_footer_text

        self._about_footer.setText(format_app_footer_text())
        self._sync_receipt_ui()
        self._sync_backup_status()
        self._sync_team_tab()
