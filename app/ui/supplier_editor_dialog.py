"""Add or edit a registered supplier (Tk)."""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from app.config import BODY_FONT, PAD_MD, SMALL_FONT
from app.services.supplier_service import SupplierService
from app.ui.theme_tokens import CTK_TEXT_DANGER, CTK_TEXT_MUTED


class SupplierEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, service: SupplierService, supplier_id: int | None = None):
        super().__init__(parent)
        self._service = service
        self._supplier_id = supplier_id
        self.saved = False

        self.title("New supplier" if supplier_id is None else "Edit supplier")
        self.geometry("440x420")
        self.minsize(400, 380)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=PAD_MD, pady=PAD_MD)

        self._name = tk.StringVar(master=self)
        self._phone = tk.StringVar(master=self)
        self._email = tk.StringVar(master=self)
        self._address = tk.StringVar(master=self)
        self._notes = tk.StringVar(master=self)

        if supplier_id is not None:
            row = service.get(int(supplier_id))
            if row:
                self._name.set(row.get("name") or "")
                self._phone.set(row.get("phone") or "")
                self._email.set(row.get("email") or "")
                self._address.set(row.get("address") or "")
                self._notes.set(row.get("notes") or "")

        r = 0
        ctk.CTkLabel(body, text="Name *", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=r, column=0, sticky="nw", pady=(0, 4)
        )
        r += 1
        ctk.CTkEntry(body, textvariable=self._name, width=360, height=32).grid(row=r, column=0, sticky="ew", pady=(0, PAD_MD))
        r += 1

        ctk.CTkLabel(body, text="Phone", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=r, column=0, sticky="nw", pady=(0, 4)
        )
        r += 1
        ctk.CTkEntry(body, textvariable=self._phone, width=360, height=32).grid(row=r, column=0, sticky="ew", pady=(0, PAD_MD))
        r += 1

        ctk.CTkLabel(body, text="Email", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=r, column=0, sticky="nw", pady=(0, 4)
        )
        r += 1
        ctk.CTkEntry(body, textvariable=self._email, width=360, height=32).grid(row=r, column=0, sticky="ew", pady=(0, PAD_MD))
        r += 1

        ctk.CTkLabel(body, text="Address", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=r, column=0, sticky="nw", pady=(0, 4)
        )
        r += 1
        ctk.CTkEntry(body, textvariable=self._address, width=360, height=32).grid(row=r, column=0, sticky="ew", pady=(0, PAD_MD))
        r += 1

        ctk.CTkLabel(body, text="Notes", font=ctk.CTkFont(family=BODY_FONT[0], size=BODY_FONT[1])).grid(
            row=r, column=0, sticky="nw", pady=(0, 4)
        )
        r += 1
        ctk.CTkEntry(body, textvariable=self._notes, width=360, height=32).grid(row=r, column=0, sticky="ew", pady=(0, PAD_MD))
        r += 1

        self._err = ctk.CTkLabel(
            body, text="", font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]), text_color=CTK_TEXT_DANGER
        )
        self._err.grid(row=r, column=0, sticky="w", pady=(0, PAD_MD))
        r += 1

        ctk.CTkLabel(
            body,
            text="* Required. This directory is for quick fill on stock receiving; receipt history still stores a snapshot.",
            font=ctk.CTkFont(family=SMALL_FONT[0], size=SMALL_FONT[1]),
            text_color=CTK_TEXT_MUTED,
            wraplength=400,
            justify="left",
        ).grid(row=r, column=0, sticky="w")

        body.columnconfigure(0, weight=1)

        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.pack(fill=tk.X, padx=PAD_MD, pady=(0, PAD_MD))
        ctk.CTkButton(btn, text="Save", width=100, command=self._save).pack(side=tk.RIGHT, padx=(PAD_MD, 0))
        ctk.CTkButton(btn, text="Cancel", width=100, fg_color="transparent", border_width=1, command=self.destroy).pack(
            side=tk.RIGHT
        )

    def _save(self) -> None:
        self._err.configure(text="")
        try:
            if self._supplier_id is None:
                self._service.create(
                    name=self._name.get(),
                    phone=self._phone.get(),
                    email=self._email.get(),
                    address=self._address.get(),
                    notes=self._notes.get(),
                )
            else:
                self._service.update(
                    self._supplier_id,
                    name=self._name.get(),
                    phone=self._phone.get(),
                    email=self._email.get(),
                    address=self._address.get(),
                    notes=self._notes.get(),
                )
        except ValueError as e:
            self._err.configure(text=str(e))
            return
        except Exception as e:
            messagebox.showerror("Supplier", str(e), parent=self)
            return
        self.saved = True
        self.destroy()
