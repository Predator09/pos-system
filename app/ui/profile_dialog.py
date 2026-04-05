"""Signed-in user: edit full name, username, and password (no owner role required)."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
from ttkbootstrap.constants import BOTH, W

from app.config import BODY_FONT, PAD_MD, SMALL_FONT
from app.services.auth_service import AuthService
from app.ui.helpers import show_message
from app.ui.theme_tokens import CTK_TEXT_DANGER, CTK_TEXT_MUTED


class ProfileDialog(ctk.CTkToplevel):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.auth = AuthService()
        self.title("My profile")
        self.geometry("440x520")
        self.minsize(400, 480)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        u = getattr(main_window, "current_user", None) or {}
        self._user_id = u.get("id")

        hint = ctk.CTkLabel(
            self,
            text="Update how your name appears in the app and your sign-in username. "
            "To change password, fill all three password fields.",
            font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]),
            text_color=CTK_TEXT_MUTED,
            wraplength=400,
        )
        hint.pack(anchor=W, padx=PAD_MD, pady=(PAD_MD, 0))

        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.pack(fill=BOTH, expand=True, padx=PAD_MD, pady=PAD_MD)

        row = 0
        self._full_var = tk.StringVar(master=self, value=u.get("full_name") or "")
        self._user_var = tk.StringVar(master=self, value=u.get("username") or "")

        ctk.CTkLabel(frm, text="Full name", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=row, column=0, sticky=W, pady=(0, 4)
        )
        row += 1
        ctk.CTkEntry(frm, textvariable=self._full_var, width=320).grid(row=row, column=0, sticky=W, pady=(0, PAD_MD))
        row += 1

        ctk.CTkLabel(frm, text="Username", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=row, column=0, sticky=W, pady=(0, 4)
        )
        row += 1
        ctk.CTkEntry(frm, textvariable=self._user_var, width=320).grid(row=row, column=0, sticky=W, pady=(0, PAD_MD))
        row += 1

        ctk.CTkLabel(
            frm,
            text="Change password (optional)",
            font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1], weight="bold"),
        ).grid(row=row, column=0, sticky=W, pady=(PAD_MD, 4))
        row += 1

        self._cur_pw = tk.StringVar(master=self)
        self._new_pw = tk.StringVar(master=self)
        self._conf_pw = tk.StringVar(master=self)

        ctk.CTkLabel(frm, text="Current password", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=row, column=0, sticky=W, pady=(0, 4)
        )
        row += 1
        ctk.CTkEntry(frm, textvariable=self._cur_pw, show="•", width=320).grid(row=row, column=0, sticky=W, pady=(0, PAD_MD))
        row += 1

        ctk.CTkLabel(frm, text="New password (min 4 characters)", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=row, column=0, sticky=W, pady=(0, 4)
        )
        row += 1
        ctk.CTkEntry(frm, textvariable=self._new_pw, show="•", width=320).grid(row=row, column=0, sticky=W, pady=(0, PAD_MD))
        row += 1

        ctk.CTkLabel(frm, text="Confirm new password", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=row, column=0, sticky=W, pady=(0, 4)
        )
        row += 1
        ctk.CTkEntry(frm, textvariable=self._conf_pw, show="•", width=320).grid(row=row, column=0, sticky=W, pady=(0, PAD_MD))
        row += 1

        self._err = ctk.CTkLabel(frm, text="", font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]), text_color=CTK_TEXT_DANGER)
        self._err.grid(row=row, column=0, sticky=W)
        row += 1

        bf = ctk.CTkFrame(frm, fg_color="transparent")
        bf.grid(row=row, column=0, sticky=W, pady=(PAD_MD, 0))
        ctk.CTkButton(bf, text="Save", command=self._save).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(bf, text="Cancel", fg_color="transparent", border_width=1, command=self._close).pack(side=LEFT)

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda e: self._close())

        self.wait_visibility(self)
        self.wait_window(self)

    def _close(self):
        self.grab_release()
        self.destroy()

    def _save(self):
        self._err.configure(text="")
        if self._user_id is None:
            self._err.configure(text="Not signed in.")
            return

        cur = (self._cur_pw.get() or "").replace("\r", "").replace("\n", "")
        new = (self._new_pw.get() or "").replace("\r", "").replace("\n", "")
        conf = (self._conf_pw.get() or "").replace("\r", "").replace("\n", "")
        any_pw = bool(cur or new or conf)
        if any_pw:
            if not cur or not new or not conf:
                self._err.configure(text="To change password, fill current, new, and confirm.")
                return
            if new != conf:
                self._err.configure(text="New password and confirmation do not match.")
                return
            if len(new.strip()) < 4:
                self._err.configure(text="New password must be at least 4 characters.")
                return

        acting = getattr(self.main_window, "current_user", None)
        try:
            snap = self.auth.update_own_profile(
                acting,
                full_name=self._full_var.get(),
                username=self._user_var.get(),
            )
        except ValueError as e:
            self._err.configure(text=str(e))
            return

        self.main_window.current_user = snap
        if hasattr(self.main_window, "refresh_header_user_display"):
            self.main_window.refresh_header_user_display()

        if any_pw:
            try:
                self.auth.change_own_password(snap, cur, new)
            except ValueError as e:
                self._err.configure(text=str(e))
                return
            self._cur_pw.set("")
            self._new_pw.set("")
            self._conf_pw.set("")

        show_message("Profile saved.", title="My profile", parent=self)
        self._close()

