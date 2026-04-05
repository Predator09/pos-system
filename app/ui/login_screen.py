import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog

import customtkinter as ctk
import ttkbootstrap as ttk
from ttkbootstrap.constants import EW

from app.config import BODY_FONT, PAD_MD, SMALL_FONT, TITLE_FONT
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
from app.ui.motion_tk import animate_corner_radius_sequence
from app.ui.theme_tokens import (
    CTK_BTN_GHOST_BORDER,
    CTK_BTN_GHOST_HOVER,
    CTK_BTN_PRIMARY_FG,
    CTK_BTN_PRIMARY_HOVER,
    CTK_CARD_BORDER,
    CTK_TEXT_DANGER,
    CTK_TEXT_MUTED,
)
from app.ui.widgets.shop_logo import ShopLogoWidget


class LoginScreen(ttk.Frame):
    """Centered sign-in; pick a shop or create one — each shop has its own database and files."""

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._suppress_shop_callback = False
        self._shop_combo_labels: list[str] = []
        self._shop_combo_ids: list[str] = []
        self.auth = AuthService()
        self._has_users = self.auth.has_any_users()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=1, column=0)

        self._logo = ShopLogoWidget(center, size=96, editable=True)
        self._logo.pack(pady=(0, PAD_MD))
        self._logo.refresh()

        shop_pick = ctk.CTkFrame(center, fg_color="transparent")
        shop_pick.pack(pady=(0, PAD_MD))
        ctk.CTkLabel(
            shop_pick,
            text="Shop",
            font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]),
            text_color=CTK_TEXT_MUTED,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self._shop_combo = ctk.CTkComboBox(
            shop_pick,
            values=["…"],
            width=220,
            height=36,
            font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1]),
            state="readonly",
            command=self._on_shop_combo_changed,
        )
        self._shop_combo.pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkButton(
            shop_pick,
            text="New shop…",
            width=96,
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color=CTK_BTN_GHOST_BORDER,
            hover_color=CTK_BTN_GHOST_HOVER,
            command=self._on_new_shop,
        ).pack(side=tk.LEFT)

        ctk.CTkLabel(
            center,
            text="Business name",
            font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]),
            text_color=CTK_TEXT_MUTED,
        ).pack(anchor="center")
        shop_row = ctk.CTkFrame(center, fg_color="transparent")
        shop_row.pack(pady=(4, 0))
        self._shop_var = tk.StringVar(master=self, value=get_display_shop_name())
        self._shop_entry = ctk.CTkEntry(
            shop_row,
            textvariable=self._shop_var,
            width=220,
            height=36,
            font=ctk.CTkFont(family=TITLE_FONT[0], size=TITLE_FONT[1], weight="bold"),
        )
        self._shop_entry.pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkButton(
            shop_row,
            text="Save",
            width=72,
            height=36,
            fg_color=CTK_BTN_PRIMARY_FG,
            hover_color=CTK_BTN_PRIMARY_HOVER,
            command=self._save_business_name,
        ).pack(side=tk.LEFT)
        self._shop_name_error = ctk.CTkLabel(
            center, text="", font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]), text_color=CTK_TEXT_DANGER
        )
        self._shop_name_error.pack(pady=(4, 0))

        self._forms_host = ctk.CTkFrame(center, fg_color="transparent")
        self._forms_host.pack(pady=(PAD_MD * 2, 0), padx=8)

        # --- Sign in ---
        self._sign_card = ctk.CTkFrame(
            self._forms_host, corner_radius=12, border_width=1, border_color=("gray75", "gray35")
        )
        ctk.CTkLabel(self._sign_card, text="Sign in", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        ctk.CTkLabel(self._sign_card, text="Username", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=1, column=0, sticky=tk.W, pady=(0, 4)
        )
        self._user_var = tk.StringVar(master=self, value="admin" if self._has_users else "")
        self._user_entry = ctk.CTkEntry(self._sign_card, textvariable=self._user_var, width=260, height=34)
        self._user_entry.grid(row=2, column=0, sticky=EW, pady=(0, PAD_MD))

        ctk.CTkLabel(self._sign_card, text="Password", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=3, column=0, sticky=tk.W, pady=(0, 4)
        )
        self._pass_var = tk.StringVar(master=self)
        self._pass_entry = ctk.CTkEntry(self._sign_card, textvariable=self._pass_var, show="•", width=260, height=34)
        self._pass_entry.grid(row=4, column=0, sticky=EW, pady=(0, PAD_MD))

        self._error = ctk.CTkLabel(
            self._sign_card, text="", font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]), text_color=CTK_TEXT_DANGER
        )
        self._error.grid(row=5, column=0, sticky=tk.W, pady=(0, PAD_MD))

        ctk.CTkButton(
            self._sign_card,
            text="Sign in",
            height=36,
            fg_color=CTK_BTN_PRIMARY_FG,
            hover_color=CTK_BTN_PRIMARY_HOVER,
            command=self._try_login,
        ).grid(row=6, column=0, sticky=EW, pady=(PAD_MD, 0))

        self._sign_card.columnconfigure(0, weight=1)
        self._user_entry.bind("<Return>", lambda e: self._pass_entry.focus_set())
        self._pass_entry.bind("<Return>", lambda e: self._try_login())

        # --- Register new shop (first device only) ---
        self._sign_up_card = ctk.CTkFrame(
            self._forms_host, corner_radius=12, border_width=1, border_color=CTK_CARD_BORDER
        )
        r = 0
        ctk.CTkLabel(self._sign_up_card, text="Add new shop", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=r, column=0, sticky="w", pady=(0, 4)
        )
        r += 1
        ctk.CTkLabel(
            self._sign_up_card,
            text="Your business name above will be used for receipts and the app. You will be the owner.",
            font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]),
            text_color=CTK_TEXT_MUTED,
            wraplength=300,
            justify="left",
        ).grid(row=r, column=0, sticky="w", pady=(0, 12))
        r += 1

        ctk.CTkLabel(self._sign_up_card, text="Your full name", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=r, column=0, sticky=tk.W, pady=(0, 4)
        )
        r += 1
        self._reg_full_var = tk.StringVar(master=self)
        self._reg_full_entry = ctk.CTkEntry(self._sign_up_card, textvariable=self._reg_full_var, width=260, height=34)
        self._reg_full_entry.grid(row=r, column=0, sticky=EW, pady=(0, PAD_MD))
        r += 1

        ctk.CTkLabel(self._sign_up_card, text="Username", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=r, column=0, sticky=tk.W, pady=(0, 4)
        )
        r += 1
        self._reg_user_var = tk.StringVar(master=self)
        self._reg_user_entry = ctk.CTkEntry(self._sign_up_card, textvariable=self._reg_user_var, width=260, height=34)
        self._reg_user_entry.grid(row=r, column=0, sticky=EW, pady=(0, PAD_MD))
        r += 1

        ctk.CTkLabel(self._sign_up_card, text="Password", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=r, column=0, sticky=tk.W, pady=(0, 4)
        )
        r += 1
        self._reg_pass_var = tk.StringVar(master=self)
        self._reg_pass_entry = ctk.CTkEntry(self._sign_up_card, textvariable=self._reg_pass_var, show="•", width=260, height=34)
        self._reg_pass_entry.grid(row=r, column=0, sticky=EW, pady=(0, PAD_MD))
        r += 1

        ctk.CTkLabel(self._sign_up_card, text="Confirm password", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=r, column=0, sticky=tk.W, pady=(0, 4)
        )
        r += 1
        self._reg_confirm_var = tk.StringVar(master=self)
        self._reg_confirm_entry = ctk.CTkEntry(
            self._sign_up_card, textvariable=self._reg_confirm_var, show="•", width=260, height=34
        )
        self._reg_confirm_entry.grid(row=r, column=0, sticky=EW, pady=(0, PAD_MD))
        r += 1

        self._reg_error = ctk.CTkLabel(
            self._sign_up_card,
            text="",
            font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]),
            text_color=CTK_TEXT_DANGER,
        )
        self._reg_error.grid(row=r, column=0, sticky=tk.W, pady=(0, PAD_MD))
        r += 1

        ctk.CTkButton(
            self._sign_up_card,
            text="Create shop & sign in",
            height=36,
            fg_color=CTK_BTN_PRIMARY_FG,
            hover_color=CTK_BTN_PRIMARY_HOVER,
            command=self._try_register,
        ).grid(row=r, column=0, sticky=EW, pady=(PAD_MD, 0))
        r += 1
        ctk.CTkButton(
            self._sign_up_card,
            text="Back to sign in",
            height=30,
            fg_color="transparent",
            border_width=1,
            border_color=CTK_BTN_GHOST_BORDER,
            hover_color=CTK_BTN_GHOST_HOVER,
            command=self._show_signin,
        ).grid(row=r, column=0, sticky=EW, pady=(10, 0))

        self._sign_up_card.columnconfigure(0, weight=1)
        self._reg_full_entry.bind("<Return>", lambda e: self._reg_user_entry.focus_set())
        self._reg_user_entry.bind("<Return>", lambda e: self._reg_pass_entry.focus_set())
        self._reg_pass_entry.bind("<Return>", lambda e: self._reg_confirm_entry.focus_set())
        self._reg_confirm_entry.bind("<Return>", lambda e: self._try_register())

        self._sign_up_card.pack_forget()
        self._sign_card.pack(fill=tk.X)
        self._populate_shop_combo()
        self._refresh_after_shop_change()

        ctk.CTkLabel(
            center,
            text=(
                "Hello 👋 How's your day? Hope it's a good one! ☀️\n\n"
                "Set your business name above — it's saved for receipts and the app. "
                "Tap the circle for your logo (right-click to remove). ✨"
            ),
            font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]),
            text_color=CTK_TEXT_MUTED,
            wraplength=360,
            justify="center",
        ).pack(pady=(PAD_MD, 0))

        animate_corner_radius_sequence(self, [self._sign_card, self._sign_up_card], start=6, end=16, step=2, delay_ms=26)

    def _populate_shop_combo(self, select_id: str | None = None) -> None:
        shops = list_shops()
        labels, ids = shop_combo_entries(shops)
        self._shop_combo_labels = labels
        self._shop_combo_ids = ids
        self._suppress_shop_callback = True
        try:
            self._shop_combo.configure(values=labels if labels else ["(no shops)"])
            want = select_id if select_id is not None else get_current_shop_id()
            if want in ids:
                self._shop_combo.set(labels[ids.index(want)])
            elif labels:
                self._shop_combo.set(labels[0])
        finally:
            self._suppress_shop_callback = False

    def _on_shop_combo_changed(self, choice: str) -> None:
        if self._suppress_shop_callback or not self._shop_combo_ids:
            return
        if choice not in self._shop_combo_labels:
            return
        idx = self._shop_combo_labels.index(choice)
        sid = self._shop_combo_ids[idx]
        if sid == get_current_shop_id():
            return
        try:
            open_shop_database(db, sid)
        except Exception as e:
            messagebox.showerror("Switch shop", str(e), parent=self.winfo_toplevel())
            self._populate_shop_combo()
            return
        self._refresh_after_shop_change()

    def _on_new_shop(self) -> None:
        name = simpledialog.askstring(
            "New shop",
            "Business / shop name:",
            parent=self.winfo_toplevel(),
        )
        if not name or not str(name).strip():
            return
        try:
            sid = create_new_shop(str(name).strip())
            open_shop_database(db, sid)
        except Exception as e:
            messagebox.showerror("New shop", str(e), parent=self.winfo_toplevel())
            return
        self._populate_shop_combo(select_id=sid)
        self._refresh_after_shop_change()

    def _refresh_after_shop_change(self) -> None:
        self.auth = AuthService()
        self._has_users = self.auth.has_any_users()
        self._shop_name_error.configure(text="")
        self._error.configure(text="")
        self._reg_error.configure(text="")
        self._shop_var.set(get_display_shop_name())
        self._logo.refresh()
        self._user_var.set("admin" if self._has_users else "")
        if not self._has_users:
            self._show_signup()
        else:
            self._show_signin()

    def _show_signup(self) -> None:
        self._error.configure(text="")
        self._reg_error.configure(text="")
        self._sign_card.pack_forget()
        self._sign_up_card.pack(fill=tk.X)
        self._reg_full_entry.focus_set()

    def _show_signin(self) -> None:
        self._reg_error.configure(text="")
        self._sign_up_card.pack_forget()
        self._sign_card.pack(fill=tk.X)
        self._pass_entry.focus_set()

    def _save_business_name(self) -> None:
        self._shop_name_error.configure(text="")
        name = (self._shop_entry.get() or self._shop_var.get() or "").strip()
        if not name:
            self._shop_name_error.configure(text="Enter a business name.")
            return
        try:
            ShopSettings().set_shop_name(name)
        except ValueError as e:
            self._shop_name_error.configure(text=str(e))
            return
        self._shop_var.set(name)

    def _try_register(self) -> None:
        self._reg_error.configure(text="")
        shop = (self._shop_entry.get() or self._shop_var.get() or "").strip()
        full = (self._reg_full_entry.get() or self._reg_full_var.get() or "").strip()
        uname = (self._reg_user_entry.get() or self._reg_user_var.get() or "").strip()
        p1 = (self._reg_pass_entry.get() or self._reg_pass_var.get() or "").replace("\r", "").replace("\n", "")
        p2 = (self._reg_confirm_entry.get() or self._reg_confirm_var.get() or "").replace("\r", "").replace("\n", "")

        if p1 != p2:
            self._reg_error.configure(text="Passwords do not match.")
            return

        try:
            user = self.auth.register_new_shop(
                shop_name=shop,
                full_name=full,
                username=uname,
                password=p1,
            )
        except ValueError as e:
            self._reg_error.configure(text=str(e))
            return
        except Exception as e:
            self._reg_error.configure(text=f"Could not register: {e}")
            return

        self._shop_var.set(get_display_shop_name())
        self._reg_pass_var.set("")
        self._reg_confirm_var.set("")
        self._reg_pass_entry.delete(0, tk.END)
        self._reg_confirm_entry.delete(0, tk.END)
        self.main_window.enter_app(user)

    def _try_login(self):
        self._error.configure(text="")
        uname = (self._user_entry.get() or self._user_var.get() or "").strip()
        pwd = (self._pass_entry.get() or self._pass_var.get() or "").replace("\r", "").replace("\n", "")

        if not uname:
            self._error.configure(text="Enter your username.")
            return

        self.auth.ensure_default_users()

        try:
            user = self.auth.authenticate(uname, pwd)
        except Exception as e:
            self._error.configure(text=f"Sign-in error: {e}")
            return

        if user:
            self._pass_var.set("")
            self._pass_entry.delete(0, tk.END)
            self.main_window.enter_app(user)
            return

        try:
            tbl = db.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if tbl is None:
                self._error.configure(
                    text=f"Users table missing. Delete {database_path()} and restart (resets this shop only)."
                )
                return

            exists = db.fetchone(
                "SELECT 1 FROM users WHERE lower(username) = lower(?) AND is_active = 1",
                (uname,),
            )
            if exists is None:
                self._error.configure(
                    text=f'No active account found for “{uname}”. Check the username or ask your store owner.'
                )
            else:
                self._error.configure(text="Wrong password. Try again or use the correct account password.")
        except sqlite3.OperationalError as e:
            self._error.configure(text=f"Database error: {e}")
