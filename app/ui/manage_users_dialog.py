"""Owner-only dialog to add staff accounts and adjust roles (local SQLite users)."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, END, LEFT, RIGHT, W, X

from app.config import BODY_FONT, PAD_MD, SMALL_FONT
from app.services.auth_service import AuthService
from app.ui.helpers import show_message
from app.ui.theme_tokens import CTK_TEXT_DANGER, CTK_TEXT_MUTED


class ManageUsersDialog(ctk.CTkToplevel):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.auth = AuthService()
        self.title("User accounts")
        self.geometry("760x460")
        self.minsize(640, 380)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        hint = ctk.CTkLabel(
            self,
            text="Each person signs in with their own username and password on the start screen.",
            font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]),
            text_color=CTK_TEXT_MUTED,
            wraplength=700,
        )
        hint.pack(anchor=W, padx=PAD_MD, pady=(PAD_MD, 0))

        tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        tree_frame.pack(fill=BOTH, expand=True, padx=PAD_MD, pady=(PAD_MD, 0))

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        self._tree = ttk.Treeview(
            tree_frame,
            columns=("username", "full_name", "role", "active"),
            show="headings",
            height=14,
            yscrollcommand=scroll.set,
        )
        scroll.config(command=self._tree.yview)
        self._tree.heading("username", text="Username")
        self._tree.heading("full_name", text="Full name")
        self._tree.heading("role", text="Role")
        self._tree.heading("active", text="Active")
        self._tree.column("username", width=140)
        self._tree.column("full_name", width=220)
        self._tree.column("role", width=90)
        self._tree.column("active", width=70)
        self._tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=tk.Y)

        self._tree.bind("<Double-1>", lambda e: self._edit_selected())

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill=X, padx=PAD_MD, pady=PAD_MD)
        ctk.CTkButton(btn_row, text="Add user…", command=self._add_user).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(btn_row, text="Edit…", fg_color="transparent", border_width=1, command=self._edit_selected).pack(
            side=LEFT, padx=(0, 8)
        )
        ctk.CTkButton(btn_row, text="Set password…", fg_color="transparent", border_width=1, command=self._set_password).pack(
            side=LEFT, padx=(0, 8)
        )
        ctk.CTkButton(btn_row, text="Close", width=90, command=self._close).pack(side=RIGHT)

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda e: self._close())

        self._reload_table()
        self.wait_visibility(self)
        self.wait_window(self)

    def _acting(self):
        return getattr(self.main_window, "current_user", None)

    def _reload_table(self):
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        try:
            rows = self.auth.list_users(self._acting())
        except ValueError as e:
            show_message(str(e), title="Users", parent=self)
            self._close()
            return
        for u in rows:
            active_txt = "Yes" if u.get("is_active") else "No"
            self._tree.insert(
                "",
                END,
                iid=str(u["id"]),
                values=(
                    u.get("username") or "",
                    u.get("full_name") or "",
                    (u.get("role") or "").title(),
                    active_txt,
                ),
            )

    def _selected_user_id(self) -> int | None:
        sel = self._tree.selection()
        if not sel:
            show_message("Select a user in the list.", title="Users", parent=self)
            return None
        return int(sel[0])

    def _add_user(self):
        win = ctk.CTkToplevel(self)
        win.title("Add user")
        win.transient(self)
        win.grab_set()
        frm = ctk.CTkFrame(win, fg_color="transparent")
        frm.pack(fill=BOTH, expand=True, padx=PAD_MD, pady=PAD_MD)

        uv = tk.StringVar(master=win)
        pv = tk.StringVar(master=win)
        nv = tk.StringVar(master=win)
        rv = tk.StringVar(master=win, value="staff")

        ctk.CTkLabel(frm, text="Username", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=0, column=0, sticky=W, pady=(0, 4)
        )
        ctk.CTkEntry(frm, textvariable=uv, width=280).grid(row=1, column=0, sticky=W, pady=(0, PAD_MD))

        ctk.CTkLabel(frm, text="Password (min 4 characters)", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=2, column=0, sticky=W, pady=(0, 4)
        )
        ctk.CTkEntry(frm, textvariable=pv, show="•", width=280).grid(row=3, column=0, sticky=W, pady=(0, PAD_MD))

        ctk.CTkLabel(frm, text="Full name", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=4, column=0, sticky=W, pady=(0, 4)
        )
        ctk.CTkEntry(frm, textvariable=nv, width=280).grid(row=5, column=0, sticky=W, pady=(0, PAD_MD))

        ctk.CTkLabel(frm, text="Role", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=6, column=0, sticky=W, pady=(0, 4)
        )
        ctk.CTkComboBox(frm, variable=rv, values=("staff", "owner"), width=260, state="readonly").grid(
            row=7, column=0, sticky=W, pady=(0, PAD_MD)
        )

        err = ctk.CTkLabel(frm, text="", font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]), text_color=CTK_TEXT_DANGER)
        err.grid(row=8, column=0, sticky=W)

        def save():
            err.configure(text="")
            try:
                self.auth.create_user(
                    self._acting(),
                    username=uv.get(),
                    password=pv.get(),
                    full_name=nv.get(),
                    role=rv.get(),
                )
            except ValueError as e:
                err.configure(text=str(e))
                return
            self._reload_table()
            win.grab_release()
            win.destroy()

        bf = ctk.CTkFrame(frm, fg_color="transparent")
        bf.grid(row=9, column=0, sticky=W, pady=(PAD_MD, 0))
        ctk.CTkButton(bf, text="Create", command=save).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(bf, text="Cancel", fg_color="transparent", border_width=1, command=lambda: (win.grab_release(), win.destroy())).pack(
            side=LEFT
        )

        win.protocol("WM_DELETE_WINDOW", lambda: (win.grab_release(), win.destroy()))
        win.bind("<Escape>", lambda e: (win.grab_release(), win.destroy()))
        win.wait_visibility(win)
        win.wait_window(win)

    def _edit_selected(self):
        uid = self._selected_user_id()
        if uid is None:
            return
        u = self.auth.get_user(self._acting(), uid)
        if not u:
            show_message("User not found.", title="Users", parent=self)
            return

        win = ctk.CTkToplevel(self)
        win.title(f"Edit — {u.get('username', '')}")
        win.transient(self)
        win.grab_set()
        frm = ctk.CTkFrame(win, fg_color="transparent")
        frm.pack(fill=BOTH, expand=True, padx=PAD_MD, pady=PAD_MD)

        ctk.CTkLabel(frm, text=f"Username: {u.get('username', '')}", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=0, column=0, sticky=W, pady=(0, PAD_MD)
        )

        nv = tk.StringVar(master=win, value=u.get("full_name") or "")
        rv = tk.StringVar(master=win, value=str(u.get("role") or "staff").lower())
        av = tk.BooleanVar(master=win, value=bool(u.get("is_active")))

        ctk.CTkLabel(frm, text="Full name", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=1, column=0, sticky=W, pady=(0, 4)
        )
        ctk.CTkEntry(frm, textvariable=nv, width=280).grid(row=2, column=0, sticky=W, pady=(0, PAD_MD))

        ctk.CTkLabel(frm, text="Role", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=3, column=0, sticky=W, pady=(0, 4)
        )
        ctk.CTkComboBox(frm, variable=rv, values=("staff", "owner"), width=260, state="readonly").grid(
            row=4, column=0, sticky=W, pady=(0, PAD_MD)
        )

        ctk.CTkCheckBox(frm, text="Account active (can sign in)", variable=av).grid(row=5, column=0, sticky=W, pady=(0, PAD_MD))

        err = ctk.CTkLabel(frm, text="", font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]), text_color=CTK_TEXT_DANGER)
        err.grid(row=6, column=0, sticky=W)

        def save():
            err.configure(text="")
            try:
                self.auth.update_user(
                    self._acting(),
                    uid,
                    full_name=nv.get(),
                    role=rv.get(),
                    is_active=av.get(),
                )
            except ValueError as e:
                err.configure(text=str(e))
                return
            self._reload_table()
            win.grab_release()
            win.destroy()

        bf = ctk.CTkFrame(frm, fg_color="transparent")
        bf.grid(row=7, column=0, sticky=W, pady=(PAD_MD, 0))
        ctk.CTkButton(bf, text="Save", command=save).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(bf, text="Cancel", fg_color="transparent", border_width=1, command=lambda: (win.grab_release(), win.destroy())).pack(
            side=LEFT
        )

        win.protocol("WM_DELETE_WINDOW", lambda: (win.grab_release(), win.destroy()))
        win.bind("<Escape>", lambda e: (win.grab_release(), win.destroy()))
        win.wait_visibility(win)
        win.wait_window(win)

    def _set_password(self):
        uid = self._selected_user_id()
        if uid is None:
            return
        u = self.auth.get_user(self._acting(), uid)
        if not u:
            show_message("User not found.", title="Users", parent=self)
            return

        win = ctk.CTkToplevel(self)
        win.title(f"New password — {u.get('username', '')}")
        win.transient(self)
        win.grab_set()
        frm = ctk.CTkFrame(win, fg_color="transparent")
        frm.pack(fill=BOTH, expand=True, padx=PAD_MD, pady=PAD_MD)

        p1 = tk.StringVar(master=win)
        p2 = tk.StringVar(master=win)
        ctk.CTkLabel(frm, text="New password (min 4 characters)", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=0, column=0, sticky=W, pady=(0, 4)
        )
        ctk.CTkEntry(frm, textvariable=p1, show="•", width=280).grid(row=1, column=0, sticky=W, pady=(0, PAD_MD))
        ctk.CTkLabel(frm, text="Confirm", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=2, column=0, sticky=W, pady=(0, 4)
        )
        ctk.CTkEntry(frm, textvariable=p2, show="•", width=280).grid(row=3, column=0, sticky=W, pady=(0, PAD_MD))

        err = ctk.CTkLabel(frm, text="", font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]), text_color=CTK_TEXT_DANGER)
        err.grid(row=4, column=0, sticky=W)

        def save():
            err.configure(text="")
            if p1.get() != p2.get():
                err.configure(text="Passwords do not match.")
                return
            try:
                self.auth.set_password(self._acting(), uid, p1.get())
            except ValueError as e:
                err.configure(text=str(e))
                return
            show_message("Password updated.", title="Users", parent=win)
            win.grab_release()
            win.destroy()

        bf = ctk.CTkFrame(frm, fg_color="transparent")
        bf.grid(row=5, column=0, sticky=W, pady=(PAD_MD, 0))
        ctk.CTkButton(bf, text="Save", command=save).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(bf, text="Cancel", fg_color="transparent", border_width=1, command=lambda: (win.grab_release(), win.destroy())).pack(
            side=LEFT
        )

        win.protocol("WM_DELETE_WINDOW", lambda: (win.grab_release(), win.destroy()))
        win.bind("<Escape>", lambda e: (win.grab_release(), win.destroy()))
        win.wait_visibility(win)
        win.wait_window(win)

    def _close(self):
        self.grab_release()
        self.destroy()
