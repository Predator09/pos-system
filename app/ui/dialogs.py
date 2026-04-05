import tkinter as tk

import customtkinter as ctk
import ttkbootstrap as ttk
from PIL import Image, ImageTk
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, X

from app.services.receipt_output import archive_receipt_file, format_receipt_plaintext, print_receipt
from app.services.shop_settings import ShopSettings
from app.ui.helpers import format_money, show_message
from app.ui.theme_tokens import CTK_TEXT_MUTED


class PickProductDialog(ctk.CTkToplevel):
    """Modal dialog to pick a product from a list (all active or a pre-filtered list)."""

    def __init__(self, parent, product_service, products=None):
        super().__init__(parent)
        self.product_service = product_service
        self.result = None
        self._all_products = list(products) if products is not None else product_service.list_products()
        self._filtered = list(self._all_products)

        self.title("Pick Product")
        self.geometry("520x420")
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._filter_var = tk.StringVar(master=self)

        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill=X, padx=12, pady=12)
        ctk.CTkLabel(search_frame, text="Filter:").pack(side=LEFT, padx=(0, 8))
        filter_entry = ctk.CTkEntry(search_frame, textvariable=self._filter_var, height=32)
        filter_entry.pack(side=LEFT, fill=X, expand=True)

        list_frame = ctk.CTkFrame(self, fg_color="transparent")
        list_frame.pack(fill=BOTH, expand=True, padx=12, pady=(0, 8))

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self._listbox = tk.Listbox(list_frame, yscrollcommand=scroll.set, height=14, exportselection=False)
        scroll.config(command=self._listbox.yview)
        self._listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=tk.Y)

        self._listbox.bind("<Double-1>", lambda e: self._ok())
        filter_entry.bind("<KeyRelease>", lambda e: self._apply_filter())
        self._populate_listbox()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill=X, padx=12, pady=(0, 12))
        ctk.CTkButton(btn_row, text="OK", width=100, command=self._ok).pack(side=RIGHT, padx=(8, 0))
        ctk.CTkButton(btn_row, text="Cancel", width=100, fg_color="transparent", border_width=1, command=self._cancel).pack(
            side=RIGHT
        )

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda e: self._cancel())
        self.wait_visibility(self)
        self.wait_window(self)

    def _apply_filter(self):
        q = self._filter_var.get().strip().lower()
        if not q:
            self._filtered = list(self._all_products)
        else:
            self._filtered = [
                p
                for p in self._all_products
                if q in (p.get("name") or "").lower() or q in (p.get("code") or "").lower()
            ]
        self._populate_listbox()

    def _populate_listbox(self):
        self._listbox.delete(0, tk.END)
        for p in self._filtered:
            line = f"{p.get('name', '')} — {p.get('code', '')} — {format_money(float(p.get('selling_price', 0)))}"
            self._listbox.insert(tk.END, line)

    def _ok(self):
        sel = self._listbox.curselection()
        if not sel:
            show_message("Select a product.", parent=self)
            return
        self.result = self._filtered[sel[0]]
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


class ReceiptPreviewDialog(ctk.CTkToplevel):
    """Modal read-only receipt summary after a sale."""

    def __init__(self, parent, sale: dict):
        super().__init__(parent)
        self._sale = sale
        self.title("Sale recorded — receipt")
        self.geometry("460x560")
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        hint = ctk.CTkLabel(
            self,
            text="Print a receipt for the customer or save a record file (archived in this shop's receipts folder).",
            wraplength=420,
            font=ctk.CTkFont(size=12),
            text_color=CTK_TEXT_MUTED,
        )
        hint.pack(anchor="w", fill=X, padx=12, pady=(12, 0))

        self._receipt_logo_photo = None
        logo_path = ShopSettings().get_logo_path()
        if logo_path:
            try:
                img = Image.open(logo_path).convert("RGBA")
                img.thumbnail((160, 160), Image.Resampling.LANCZOS)
                self._receipt_logo_photo = ImageTk.PhotoImage(img)
                tk.Label(self, image=self._receipt_logo_photo).pack(pady=(8, 4))
            except OSError:
                pass

        text = tk.Text(self, wrap=tk.WORD, height=20, padx=10, pady=10)
        text.pack(fill=BOTH, expand=True, padx=12, pady=(8, 0))
        text.insert(tk.END, format_receipt_plaintext(sale))
        text.config(state=tk.DISABLED)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill=X, padx=12, pady=(8, 12))
        ctk.CTkButton(row, text="Print receipt", command=self._do_print).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(row, text="Save record", command=self._do_save).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(row, text="Done", command=self._close).pack(side=RIGHT)

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda e: self._close())
        self.wait_visibility(self)
        self._bring_receipt_to_front()
        self.wait_window(self)

    def _bring_receipt_to_front(self) -> None:
        try:
            self.update_idletasks()
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(120, self._drop_topmost)
        except tk.TclError:
            pass

    def _drop_topmost(self) -> None:
        try:
            if self.winfo_exists():
                self.attributes("-topmost", False)
        except tk.TclError:
            pass

    def _do_print(self):
        ok, msg = print_receipt(self._sale)
        show_message(msg, title="Print" if ok else "Print failed", parent=self)

    def _do_save(self):
        ok, msg = archive_receipt_file(self._sale)
        show_message(msg, title="Record saved" if ok else "Save failed", parent=self)

    def _close(self):
        self.grab_release()
        self.destroy()


class RecallParkedDialog(ctk.CTkToplevel):
    """Pick a parked sale ticket to recall."""

    def __init__(self, parent, tickets: list[dict]):
        super().__init__(parent)
        self.result: int | None = None
        self._tickets = list(tickets)

        self.title("Parked sales")
        self.geometry("520x360")
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        ctk.CTkLabel(
            self,
            text="Select a ticket to recall (double-click or OK):",
        ).pack(anchor="w", padx=12, pady=(12, 4))

        list_frame = ctk.CTkFrame(self, fg_color="transparent")
        list_frame.pack(fill=BOTH, expand=True, padx=12, pady=(0, 8))

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self._lb = tk.Listbox(list_frame, yscrollcommand=scroll.set, height=12, exportselection=False)
        scroll.config(command=self._lb.yview)
        self._lb.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=tk.Y)

        for i, t in enumerate(self._tickets):
            self._lb.insert(tk.END, t.get("summary", f"Ticket {i + 1}"))

        self._lb.bind("<Double-1>", lambda e: self._ok())
        self._lb.selection_set(0)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill=X, padx=12, pady=(0, 12))
        ctk.CTkButton(btn_row, text="Recall", width=100, command=self._ok).pack(side=RIGHT, padx=(8, 0))
        ctk.CTkButton(btn_row, text="Cancel", width=100, fg_color="transparent", border_width=1, command=self._cancel).pack(
            side=RIGHT
        )

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda e: self._cancel())
        self.wait_visibility(self)
        self.wait_window(self)

    def _ok(self):
        sel = self._lb.curselection()
        if not sel:
            show_message("Select a parked sale.", parent=self)
            return
        self.result = int(sel[0])
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()
