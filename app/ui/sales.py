"""Point of sale register: barcode-first lookup, stock-aware cart, tender & change."""

from __future__ import annotations

import copy
import tkinter as tk
import uuid
from datetime import datetime
from tkinter import messagebox, simpledialog

import customtkinter as ctk
import ttkbootstrap as ttk
from ttkbootstrap.constants import E, EW, HORIZONTAL, LEFT, NSEW, RIGHT, VERTICAL, W, X

from app.config import PAD_LG, PAD_MD, PAD_SM
from app.ui.theme_tokens import CTK_BTN_PRIMARY_FG, CTK_BTN_PRIMARY_HOVER, CTK_TEXT_MUTED
from app.services.parked_sales_service import MAX_PARKED_TICKETS, ParkedSalesService
from app.services.product_service import ProductService
from app.services.sales_service import SalesService
from app.ui.dialogs import PickProductDialog, ReceiptPreviewDialog, RecallParkedDialog
from app.ui.helpers import format_money, show_message

_CART_COLS = ("code", "name", "qty", "price", "disc", "total")
# Cart table: compact when empty, grows with line count (capped; scroll beyond).
_CART_TREE_MIN_ROWS = 3
_CART_TREE_MAX_ROWS = 16


class SaleScreen(ttk.Frame):
    """Retail register UI: grid layout, tree cart, cash tender validation."""

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._sales = SalesService()
        self._products = ProductService()
        self._parked_svc = ParkedSalesService()
        self.cart: list[dict] = []
        self._parked: list[dict] = []
        self._kpi_labels: dict[str, ctk.CTkLabel] = {}
        self._clock_after: str | None = None

        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1, minsize=280)

        self._qty_var = tk.StringVar(master=self, value="1")
        self._search_var = tk.StringVar(master=self)
        self._payment_var = tk.StringVar(master=self, value="CASH")
        self._customer_var = tk.StringVar(master=self)
        self._tender_var = tk.StringVar(master=self)

        self._build_kpis()
        self._build_register_pane()
        self._build_totals_pane()

        self._tender_var.trace_add("write", lambda *_: self._update_tender_display())
        self.bind("<Destroy>", self._on_destroy, add=True)

    def _on_destroy(self, event):
        if event.widget is not self:
            return
        if self._clock_after is not None:
            try:
                self.after_cancel(self._clock_after)
            except tk.TclError:
                pass
            self._clock_after = None

    def _on_search_return(self, event: tk.Event) -> str | None:
        self._on_add_product()
        return None

    # --- layout ---

    def _start_clock(self):
        def tick():
            if not self.winfo_exists():
                return
            if self._clock_label is not None:
                try:
                    self._clock_label.configure(text=datetime.now().strftime("%H:%M:%S"))
                except tk.TclError:
                    return
            self._clock_after = self.after(1000, tick)

        tick()

    def _build_kpis(self):
        strip = ttk.Labelframe(
            self,
            text="Today",
            bootstyle="secondary",
            padding=(PAD_SM, 6),
        )
        strip.grid(row=0, column=0, columnspan=2, sticky=EW, padx=PAD_LG, pady=(PAD_MD, PAD_SM))
        strip_inner = ctk.CTkFrame(strip, fg_color="transparent")
        strip_inner.pack(fill=X)
        strip_inner.columnconfigure(0, weight=1)

        box = ctk.CTkFrame(strip_inner, fg_color="transparent")
        box.grid(row=0, column=0, sticky=EW)
        for c in range(5):
            box.columnconfigure(c, weight=1)

        specs = [
            ("invoices", "Invoices", "primary"),
            ("gross", "Gross", "success"),
            ("cash", "Cash", "warning"),
            ("lines", "Cart lines", "secondary"),
            ("parked", "Parked", "info"),
        ]
        for i, (key, title, style) in enumerate(specs):
            cell = ctk.CTkFrame(box, fg_color="transparent")
            cell.grid(row=0, column=i, sticky=NSEW, padx=(0, PAD_MD) if i < 4 else (0, 0))
            ctk.CTkLabel(
                cell,
                text=title,
                font=ctk.CTkFont(family="Segoe UI", size=9),
                text_color=CTK_TEXT_MUTED,
            ).pack(anchor="w")
            lab = ctk.CTkLabel(cell, text="—", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
            lab.pack(anchor="w")
            self._kpi_labels[key] = lab

        self._clock_label = ctk.CTkLabel(
            strip_inner,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=CTK_TEXT_MUTED,
        )
        self._clock_label.grid(row=0, column=1, sticky=E, padx=(PAD_MD, 0))
        self._start_clock()

    def _build_register_pane(self):
        reg = ctk.CTkFrame(self, fg_color="transparent")
        reg.grid(row=1, column=0, sticky="new", padx=(PAD_LG, PAD_SM), pady=(0, PAD_LG))
        reg.columnconfigure(0, weight=1)

        entry_row = ctk.CTkFrame(reg, fg_color="transparent")
        entry_row.grid(row=0, column=0, sticky=EW, pady=(0, PAD_SM))
        entry_row.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            entry_row,
            text="Qty",
            font=ctk.CTkFont(size=11),
            text_color=CTK_TEXT_MUTED,
        ).grid(row=0, column=0, sticky=W)
        ctk.CTkLabel(
            entry_row,
            text="Lookup",
            font=ctk.CTkFont(size=11),
            text_color=CTK_TEXT_MUTED,
        ).grid(row=0, column=1, sticky=W)
        ttk.Spinbox(entry_row, from_=0.01, to=9999, increment=1, width=8, textvariable=self._qty_var).grid(
            row=1, column=0, sticky=NW, padx=(0, PAD_MD)
        )

        self._search_wrap = ctk.CTkFrame(entry_row, fg_color="transparent")
        self._search_wrap.grid(row=1, column=1, sticky=EW, padx=(0, PAD_SM))
        self._search_wrap.columnconfigure(0, weight=1)

        self._search_entry = ctk.CTkEntry(
            self._search_wrap,
            textvariable=self._search_var,
            height=36,
            font=ctk.CTkFont(size=14),
            placeholder_text="SKU, barcode, or name…",
        )
        self._search_entry.grid(row=0, column=0, sticky=EW)

        self._search_entry.bind("<Return>", self._on_search_return)
        self._search_entry.bind("<Control-Return>", lambda e: self._complete_sale())
        self._search_entry.bind("<FocusIn>", lambda e: self._search_entry.select_range(0, tk.END))
        self._search_entry.bind("<F5>", lambda e: self._park_sale())
        self._search_entry.bind("<F6>", lambda e: self._recall_parked())

        ctk.CTkButton(
            entry_row,
            text="Add",
            width=76,
            height=36,
            fg_color=CTK_BTN_PRIMARY_FG,
            hover_color=CTK_BTN_PRIMARY_HOVER,
            command=self._on_add_product,
        ).grid(row=1, column=2, sticky=NE, padx=(PAD_SM, 8))
        ctk.CTkButton(
            entry_row,
            text="Browse",
            width=88,
            height=36,
            fg_color="transparent",
            border_width=2,
            command=self._pick_product,
        ).grid(row=1, column=3, sticky=NW)

        cust = ctk.CTkFrame(reg, fg_color="transparent")
        cust.grid(row=1, column=0, sticky=EW, pady=(0, PAD_SM))
        cust.columnconfigure(1, weight=1)
        ctk.CTkLabel(
            cust,
            text="Customer (optional)",
            font=ctk.CTkFont(size=11),
            text_color=CTK_TEXT_MUTED,
        ).grid(row=0, column=0, sticky=W)
        ctk.CTkEntry(cust, textvariable=self._customer_var, height=34).grid(row=0, column=1, sticky=EW, padx=(PAD_SM, 0))

        table_wrap = ctk.CTkFrame(reg, fg_color="transparent")
        table_wrap.grid(row=2, column=0, sticky="new", pady=(0, PAD_SM))
        table_wrap.columnconfigure(0, weight=1)

        sy = ttk.Scrollbar(table_wrap, orient=VERTICAL)
        sy.grid(row=0, column=1, sticky="ns")
        self._tree = ttk.Treeview(
            table_wrap,
            columns=_CART_COLS,
            show="headings",
            selectmode="browse",
            yscrollcommand=sy.set,
            height=_CART_TREE_MIN_ROWS,
        )
        sy.config(command=self._tree.yview)
        self._tree.grid(row=0, column=0, sticky="new")

        cw = {"code": 96, "name": 260, "qty": 52, "price": 84, "disc": 68, "total": 92}
        titles = {"code": "Code", "name": "Product", "qty": "Qty", "price": "Price", "disc": "Disc", "total": "Line"}
        for c in _CART_COLS:
            self._tree.heading(c, text=titles[c])
            anchor = W if c == "name" else "center"
            self._tree.column(c, width=cw[c], anchor=anchor)

        self._tree.bind("<Double-1>", lambda e: self._edit_line_qty())
        self._tree.bind("<plus>", lambda e: self._bump_qty(1))
        self._tree.bind("<KP_Add>", lambda e: self._bump_qty(1))
        self._tree.bind("<minus>", lambda e: self._bump_qty(-1))
        self._tree.bind("<KP_Subtract>", lambda e: self._bump_qty(-1))
        self._tree.bind("<Delete>", lambda e: self._remove_selected_line())
        self._tree.bind("<F5>", lambda e: self._park_sale())
        self._tree.bind("<F6>", lambda e: self._recall_parked())

        bar = ctk.CTkFrame(reg, fg_color="transparent")
        bar.grid(row=3, column=0, sticky=EW)
        bar.columnconfigure(6, weight=1)

        def _btn(parent, text, cmd, **kw):
            return ctk.CTkButton(parent, text=text, height=30, command=cmd, **kw)

        ctk.CTkLabel(bar, text="Line", font=ctk.CTkFont(size=10, weight="bold"), text_color=CTK_TEXT_MUTED).grid(
            row=0, column=0, padx=(0, PAD_SM), sticky=W
        )
        _btn(bar, "Set qty", self._edit_line_qty, width=80, fg_color="transparent", border_width=1).grid(
            row=0, column=1, padx=(0, PAD_SM)
        )
        _btn(
            bar,
            "Discount",
            self._line_discount,
            width=88,
            fg_color=("#E8A317", "#B87D0A"),
            hover_color=("#D49412", "#9A6A08"),
        ).grid(row=0, column=2, padx=(0, PAD_SM))
        _btn(
            bar,
            "Remove",
            self._remove_selected_line,
            width=80,
            fg_color=("#C1121F", "#9A0E18"),
            hover_color=("#A00F1A", "#7D0C14"),
        ).grid(row=0, column=3, padx=(0, PAD_MD))

        ctk.CTkLabel(bar, text="Ticket", font=ctk.CTkFont(size=10, weight="bold"), text_color=CTK_TEXT_MUTED).grid(
            row=1, column=0, padx=(0, PAD_SM), pady=(PAD_SM, 0), sticky=W
        )
        _btn(bar, "Park", self._park_sale, width=80, fg_color="transparent", border_width=1).grid(
            row=1, column=1, padx=(0, 4), pady=(PAD_SM, 0), sticky=W
        )
        _btn(bar, "Recall", self._recall_parked, width=80, fg_color="transparent", border_width=1).grid(
            row=1, column=2, padx=(0, PAD_SM), pady=(PAD_SM, 0), sticky=W
        )
        _btn(
            bar,
            "Clear cart",
            self._confirm_clear_cart,
            width=100,
            fg_color="transparent",
            border_width=2,
            border_color=("#CC0000", "#992222"),
            text_color=("#B00020", "#FF6B6B"),
            hover_color=("gray90", "gray28"),
        ).grid(row=1, column=6, padx=(PAD_MD, 0), pady=(PAD_SM, 0), sticky=E)

        self.bind("<F2>", lambda e: self._focus_search())
        self._tree.bind("<F2>", lambda e: self._focus_search())
        self.bind("<F3>", lambda e: self._line_discount())
        self._tree.bind("<F3>", lambda e: self._line_discount())
        self.bind("<F4>", lambda e: self._focus_tender())
        self.bind("<F5>", lambda e: self._park_sale())
        self.bind("<F6>", lambda e: self._recall_parked())
        self.bind("<Control-Return>", lambda e: self._complete_sale())
        self.bind("<Control-KP_Enter>", lambda e: self._complete_sale())

    def _build_totals_pane(self):
        side = ttk.Labelframe(
            self,
            text="Checkout",
            bootstyle="primary",
            padding=PAD_MD,
        )
        side.grid(row=1, column=1, sticky="new", padx=(0, PAD_LG), pady=(0, PAD_LG))
        inner = ctk.CTkFrame(side, fg_color="transparent")
        inner.pack(fill=X)

        sum_box = ctk.CTkFrame(inner, fg_color="transparent")
        sum_box.pack(fill=X)

        def money_row(parent, title, attr, size=13, bold=False):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill=X, pady=(2, 0))
            ctk.CTkLabel(row, text=title, font=ctk.CTkFont(family="Segoe UI", size=11)).pack(side=LEFT)
            if bold:
                val_font = ctk.CTkFont(family="Segoe UI", size=size, weight="bold")
            else:
                val_font = ctk.CTkFont(family="Segoe UI", size=size)
            lbl = ctk.CTkLabel(row, text=format_money(0), font=val_font)
            lbl.pack(side=RIGHT)
            setattr(self, attr, lbl)

        money_row(sum_box, "Subtotal", "_subtotal_label", 12)
        money_row(sum_box, "Line discounts", "_disc_label", 11)
        ttk.Separator(inner, orient=HORIZONTAL).pack(fill=X, pady=PAD_MD)
        tot_row = ctk.CTkFrame(inner, fg_color="transparent")
        tot_row.pack(fill=X, pady=(0, 4))
        ctk.CTkLabel(tot_row, text="Total", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side=LEFT)
        self._total_label = ctk.CTkLabel(
            tot_row,
            text=format_money(0),
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
        )
        self._total_label.pack(side=RIGHT)

        pay = ctk.CTkFrame(inner, fg_color="transparent")
        pay.pack(fill=X)
        for col in range(2):
            pay.columnconfigure(col, weight=1)
        opts = (("Cash", "CASH"), ("Card", "CARD"), ("Mobile", "MOBILE"), ("Check", "CHECK"))
        for i, (text, val) in enumerate(opts):
            ctk.CTkRadioButton(
                pay,
                text=text,
                variable=self._payment_var,
                value=val,
                command=self._on_payment_change,
            ).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, PAD_MD), pady=2)

        self._tender_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self._tender_frame.pack(fill=X, pady=(PAD_MD, 0))
        ctk.CTkLabel(self._tender_frame, text="Amount received", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self._tender_entry = ctk.CTkEntry(
            self._tender_frame,
            textvariable=self._tender_var,
            height=36,
            font=ctk.CTkFont(size=15),
        )
        self._tender_entry.pack(fill=X, pady=(4, 0))
        self._tender_entry.bind("<Control-Return>", lambda e: self._complete_sale())
        ch_row = ctk.CTkFrame(self._tender_frame, fg_color="transparent")
        ch_row.pack(fill=X, pady=(PAD_SM, 0))
        ctk.CTkLabel(ch_row, text="Change", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(side=LEFT)
        self._change_label = ctk.CTkLabel(
            ch_row,
            text=format_money(0),
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
        )
        self._change_label.pack(side=RIGHT)

        self._payment_var.trace_add("write", lambda *_: self._on_payment_change())

        ctk.CTkButton(
            inner,
            text="Complete sale",
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._complete_sale,
        ).pack(fill=X, pady=(0, PAD_SM))
        ctk.CTkButton(
            inner,
            text="New cart",
            height=34,
            fg_color="transparent",
            border_width=2,
            border_color=("gray65", "gray40"),
            command=self._confirm_clear_cart,
        ).pack(fill=X)

        self._on_payment_change()

    # --- product resolution ---

    def _parse_qty(self) -> float:
        try:
            q = float(str(self._qty_var.get()).strip().replace(",", ""))
            if q <= 0:
                raise ValueError
            return q
        except ValueError:
            return 0.0

    def _qty_in_cart_for(self, product_id: int) -> float:
        t = 0.0
        for it in self.cart:
            if it["product_id"] == product_id:
                t += float(it["quantity"])
        return t

    def _resolve_product(self, query: str) -> dict | list | None:
        q = query.strip()
        if not q:
            return None
        by_code = self._products.get_product_by_code(q)
        if by_code:
            return by_code
        if len(q) < 2:
            return []
        return self._products.search_products(q)

    def _ensure_sellable(self, p: dict) -> bool:
        if not p.get("is_active"):
            show_message("This product is inactive.", parent=self.winfo_toplevel())
            return False
        return True

    def _role_can_override_stock(self) -> bool:
        u = getattr(self.main_window, "current_user", None) or {}
        return str(u.get("role") or "").lower() == "owner"

    def _offer_stock_override(self, title: str, body: str) -> bool:
        if not self._role_can_override_stock():
            return False
        return messagebox.askyesno(
            title,
            body + "\n\nOwner override: allow this sale anyway?",
            parent=self.winfo_toplevel(),
        )

    def _stock_available(self, p: dict, add_qty: float) -> bool:
        pid = int(p["id"])
        have = float(p.get("quantity_in_stock") or 0)
        in_cart = self._qty_in_cart_for(pid)
        if in_cart + add_qty <= have + 1e-9:
            return True
        detail = (
            f"Not enough stock for {p.get('name', '')}.\n"
            f"On hand: {have:g}, already in cart: {in_cart:g}, adding: {add_qty:g}."
        )
        if self._offer_stock_override("Stock", detail):
            return True
        show_message(detail.replace("\n", " "), parent=self.winfo_toplevel())
        return False

    def _line_qty_stock_ok(self, product_id: int, current_line_qty: float, new_line_qty: float) -> bool:
        p = self._products.get_product(product_id)
        if not p:
            return True
        have = float(p.get("quantity_in_stock") or 0)
        in_other = self._qty_in_cart_for(product_id) - float(current_line_qty)
        need = in_other + float(new_line_qty)
        if need <= have + 1e-9:
            return True
        detail = (
            f"Not enough stock for {p.get('name', '')}.\n"
            f"On hand: {have:g}, need for this line: {need:g}."
        )
        if self._offer_stock_override("Stock", detail):
            return True
        show_message(detail.replace("\n", " "), parent=self.winfo_toplevel())
        return False

    def _on_add_product(self):
        query = self._search_var.get()
        qty = self._parse_qty()
        if qty <= 0:
            show_message("Enter a valid quantity (> 0).", parent=self.winfo_toplevel())
            return

        resolved = self._resolve_product(query)
        if resolved is None:
            return
        if isinstance(resolved, list):
            if not resolved:
                show_message("No matching active products.", parent=self.winfo_toplevel())
                return
            if len(resolved) == 1:
                p = resolved[0]
            else:
                d = PickProductDialog(self.winfo_toplevel(), self._products, products=resolved)
                if not d.result:
                    return
                p = d.result
        else:
            p = resolved

        if not self._ensure_sellable(p):
            return
        if not self._stock_available(p, qty):
            return

        self._add_line(
            int(p["id"]),
            p.get("code") or "",
            p.get("name") or "",
            float(p.get("selling_price") or 0),
            qty,
        )
        self._search_var.set("")
        self._qty_var.set("1")
        self._search_entry.focus_set()
        self._refresh_cart_tree()

    def _pick_product(self):
        d = PickProductDialog(self.winfo_toplevel(), self._products)
        if not d.result:
            return
        p = d.result
        qty = self._parse_qty()
        if qty <= 0:
            qty = 1.0
        if not self._ensure_sellable(p):
            return
        if not self._stock_available(p, qty):
            return
        self._add_line(
            int(p["id"]),
            p.get("code") or "",
            p.get("name") or "",
            float(p.get("selling_price") or 0),
            qty,
        )
        self._refresh_cart_tree()

    def add_to_cart_by_product_id(self, product_id: int, quantity: float = 1.0) -> None:
        """Add one catalog line from gallery or external callers (qty merged if SKU already in cart)."""
        q = float(quantity)
        if q <= 0:
            show_message("Quantity must be greater than zero.", parent=self.winfo_toplevel())
            return
        p = self._products.get_product(int(product_id))
        if not p:
            show_message("Product not found.", parent=self.winfo_toplevel())
            return
        if not self._ensure_sellable(p):
            return
        if not self._stock_available(p, q):
            return
        self._add_line(
            int(p["id"]),
            p.get("code") or "",
            p.get("name") or "",
            float(p.get("selling_price") or 0),
            q,
        )
        try:
            self._search_entry.focus_set()
        except tk.TclError:
            pass

    def _add_line(self, product_id: int, code: str, name: str, unit_price: float, quantity: float):
        for it in self.cart:
            if it["product_id"] == product_id:
                it["quantity"] = float(it["quantity"]) + quantity
                it["total"] = self._line_total(it)
                self._refresh_cart_tree()
                self._update_totals()
                return
        self.cart.append(
            {
                "product_id": product_id,
                "code": code,
                "name": name,
                "unit_price": unit_price,
                "quantity": quantity,
                "discount_amount": 0.0,
                "total": 0.0,
            }
        )
        self.cart[-1]["total"] = self._line_total(self.cart[-1])
        self._refresh_cart_tree()
        self._update_totals()

    @staticmethod
    def _line_total(item: dict) -> float:
        gross = float(item["quantity"]) * float(item["unit_price"])
        disc = float(item.get("discount_amount") or 0)
        return round(max(0.0, gross - disc), 2)

    def _cart_index_from_iid(self, iid: str) -> int | None:
        try:
            return int(iid)
        except ValueError:
            return None

    def _selected_index(self) -> int | None:
        sel = self._tree.selection()
        if not sel:
            return None
        return self._cart_index_from_iid(sel[0])

    def _bump_qty(self, delta: float):
        idx = self._selected_index()
        if idx is None or idx < 0 or idx >= len(self.cart):
            return
        it = self.cart[idx]
        new_q = float(it["quantity"]) + delta
        if new_q <= 0:
            self.cart.pop(idx)
            self._refresh_cart_tree()
            self._update_totals()
            return
        if not self._line_qty_stock_ok(it["product_id"], float(it["quantity"]), new_q):
            return
        it["quantity"] = new_q
        it["total"] = self._line_total(it)
        self._refresh_cart_tree()
        self._select_index(min(idx, len(self.cart) - 1))
        self._update_totals()

    def _edit_line_qty(self):
        idx = self._selected_index()
        if idx is None:
            show_message("Select a cart line.", parent=self.winfo_toplevel())
            return
        it = self.cart[idx]
        v = simpledialog.askfloat(
            "Quantity",
            f"New qty for {it.get('name', '')}:",
            initialvalue=float(it["quantity"]),
            parent=self.winfo_toplevel(),
        )
        if v is None:
            return
        if v <= 0:
            self.cart.pop(idx)
            self._refresh_cart_tree()
            self._update_totals()
            return
        if not self._line_qty_stock_ok(it["product_id"], float(it["quantity"]), float(v)):
            return
        it["quantity"] = float(v)
        it["total"] = self._line_total(it)
        self._refresh_cart_tree()
        self._select_index(idx)
        self._update_totals()

    def _line_discount(self):
        idx = self._selected_index()
        if idx is None:
            show_message("Select a cart line.", parent=self.winfo_toplevel())
            return
        it = self.cart[idx]
        gross = float(it["quantity"]) * float(it["unit_price"])
        v = simpledialog.askfloat(
            "Line discount",
            f"Discount (GMD) for line (max {format_money(gross)}):",
            initialvalue=float(it.get("discount_amount") or 0),
            parent=self.winfo_toplevel(),
        )
        if v is None:
            return
        v = max(0.0, min(float(v), gross))
        it["discount_amount"] = round(v, 2)
        it["total"] = self._line_total(it)
        self._refresh_cart_tree()
        self._select_index(idx)
        self._update_totals()

    def _remove_selected_line(self):
        idx = self._selected_index()
        if idx is None:
            return
        self.cart.pop(idx)
        self._refresh_cart_tree()
        self._update_totals()

    def _confirm_clear_cart(self):
        if not self.cart:
            return
        if messagebox.askyesno("Clear cart", "Remove all lines?", parent=self.winfo_toplevel()):
            self.clear_cart()

    def _refresh_cart_tree(self):
        self._tree.delete(*self._tree.get_children())
        for i, it in enumerate(self.cart):
            it["total"] = self._line_total(it)
            self._tree.insert(
                "",
                tk.END,
                iid=str(i),
                values=(
                    it.get("code", ""),
                    it.get("name", ""),
                    f"{it['quantity']:g}" if float(it['quantity']) == int(float(it['quantity'])) else f"{it['quantity']:.2f}",
                    format_money(float(it["unit_price"])),
                    format_money(float(it.get("discount_amount") or 0)),
                    format_money(float(it["total"])),
                ),
            )
        self._sync_cart_tree_height()
        self._update_kpis_cart_lines()
        self._update_totals()

    def _sync_cart_tree_height(self) -> None:
        n = len(self.cart)
        vis = min(max(n, _CART_TREE_MIN_ROWS), _CART_TREE_MAX_ROWS)
        try:
            self._tree.configure(height=vis)
        except tk.TclError:
            return
        inner = getattr(self.main_window, "_scrollable_inner", None)
        if inner is not None:
            self.after_idle(lambda w=inner: w.event_generate("<Configure>"))

    def _select_index(self, idx: int):
        if 0 <= idx < len(self.cart):
            self._tree.selection_set(str(idx))
            self._tree.see(str(idx))

    def _update_totals(self):
        t = self._sales.calculate_cart_total(self.cart)
        self._subtotal_label.configure(text=format_money(t["subtotal"]))
        line_disc = sum(float(x.get("discount_amount") or 0) for x in self.cart)
        self._disc_label.configure(text=format_money(line_disc))
        self._total_label.configure(text=format_money(t["total"]))
        self._update_tender_display()

    def _on_payment_change(self):
        is_cash = self._payment_var.get() == "CASH"
        if is_cash:
            self._tender_frame.pack(fill=X, pady=(PAD_MD, 0))
        else:
            self._tender_frame.pack_forget()
            self._tender_var.set("")
        self._update_tender_display()

    def _update_tender_display(self):
        if not hasattr(self, "_change_label"):
            return
        t = self._sales.calculate_cart_total(self.cart)
        total = t["total"]
        if self._payment_var.get() != "CASH":
            self._change_label.configure(text="—")
            return
        raw = str(self._tender_var.get()).strip().replace(",", "")
        if not raw:
            self._change_label.configure(text=format_money(0))
            return
        try:
            paid = float(raw)
        except ValueError:
            self._change_label.configure(text="—")
            return
        self._change_label.configure(text=format_money(max(0.0, paid - total)))

    def _focus_search(self):
        self._search_entry.focus_set()
        self._search_entry.select_range(0, tk.END)
        return "break"

    def _focus_tender(self):
        if self._payment_var.get() == "CASH":
            self._tender_entry.focus_set()
            self._tender_entry.select_range(0, tk.END)
        return "break"

    def _complete_sale(self):
        if not self.cart:
            show_message("Cart is empty.", parent=self.winfo_toplevel())
            return
        self._refresh_cart_tree()
        totals = self._sales.calculate_cart_total(self.cart)
        total = totals["total"]
        method = self._payment_var.get()

        if method == "CASH":
            raw = str(self._tender_var.get()).strip().replace(",", "")
            if not raw:
                show_message("Enter amount received for cash sales.", parent=self.winfo_toplevel())
                self._focus_tender()
                return
            try:
                paid = float(raw)
            except ValueError:
                show_message("Invalid amount received.", parent=self.winfo_toplevel())
                return
            if paid + 1e-9 < total:
                show_message(
                    f"Insufficient tender. Need {format_money(total)}, got {format_money(paid)}.",
                    parent=self.winfo_toplevel(),
                )
                return

        try:
            sale = self._sales.record_sale(
                self.cart,
                {
                    "method": method,
                    "customer_name": self._customer_var.get().strip(),
                },
            )
        except Exception as e:
            show_message(f"Sale failed: {e}", parent=self.winfo_toplevel())
            return

        if sale:
            ReceiptPreviewDialog(self.main_window, sale)
        self.clear_cart()
        self.refresh()

    def clear_cart(self):
        self.cart = []
        self._tender_var.set("")
        self._customer_var.set("")
        self._refresh_cart_tree()

    def _update_kpis_cart_lines(self):
        if "lines" in self._kpi_labels:
            self._kpi_labels["lines"].configure(text=str(len(self.cart)))

    def _update_parked_kpi(self):
        if "parked" in self._kpi_labels:
            self._kpi_labels["parked"].configure(text=str(len(self._parked)))

    def _refresh_parked_from_db(self):
        self._parked = self._parked_svc.list_tickets()
        self._update_parked_kpi()

    def _park_sale(self):
        if not self.cart:
            show_message("Cart is empty — nothing to park.", parent=self.winfo_toplevel())
            return
        if self._parked_svc.count() >= MAX_PARKED_TICKETS:
            show_message(
                f"Maximum {MAX_PARKED_TICKETS} parked tickets. Recall or complete one first.",
                parent=self.winfo_toplevel(),
            )
            return
        tid = uuid.uuid4().hex[:10]
        cart_snapshot = copy.deepcopy(self.cart)
        try:
            self._parked_svc.insert(
                tid,
                cart_snapshot,
                self._customer_var.get(),
                self._payment_var.get(),
                self._tender_var.get(),
            )
        except ValueError as e:
            show_message(str(e), parent=self.winfo_toplevel())
            return
        except Exception as e:
            show_message(f"Could not park sale: {e}", parent=self.winfo_toplevel())
            return
        self.clear_cart()
        self._refresh_parked_from_db()
        show_message(f"Parked ticket {tid} (saved).", parent=self.winfo_toplevel())
        try:
            self._search_entry.focus_set()
        except tk.TclError:
            pass

    def _restore_ticket(self, ticket: dict) -> None:
        self.cart = copy.deepcopy(ticket.get("cart") or [])
        self._customer_var.set(ticket.get("customer") or "")
        self._payment_var.set(ticket.get("payment") or "CASH")
        self._tender_var.set(ticket.get("tender") or "")
        self._on_payment_change()
        self._refresh_cart_tree()

    def _merge_ticket_lines(self, ticket: dict) -> bool:
        for src in ticket.get("cart") or []:
            p = self._products.get_product(int(src["product_id"]))
            if not p:
                show_message(
                    f"Product #{src['product_id']} missing — merge aborted.",
                    parent=self.winfo_toplevel(),
                )
                return False
            if not self._ensure_sellable(p):
                return False
            q = float(src["quantity"])
            if not self._stock_available(p, q):
                return False
        for src in ticket.get("cart") or []:
            pid = int(src["product_id"])
            up = float(src["unit_price"])
            disc = float(src.get("discount_amount") or 0)
            q = float(src["quantity"])
            merged = False
            for it in self.cart:
                if (
                    it["product_id"] == pid
                    and abs(float(it["unit_price"]) - up) < 1e-9
                    and abs(float(it.get("discount_amount") or 0) - disc) < 1e-9
                ):
                    it["quantity"] = float(it["quantity"]) + q
                    it["total"] = self._line_total(it)
                    merged = True
                    break
            if not merged:
                nl = copy.deepcopy(src)
                nl["total"] = self._line_total(nl)
                self.cart.append(nl)
        self._refresh_cart_tree()
        return True

    def _recall_parked(self):
        if not self._parked:
            show_message("No parked sales.", parent=self.winfo_toplevel())
            return
        d = RecallParkedDialog(self.winfo_toplevel(), self._parked)
        if d.result is None:
            return
        idx = d.result
        ticket = self._parked.pop(idx)
        if self.cart:
            r = messagebox.askyesnocancel(
                "Current cart",
                "Replace current cart with the parked sale?\n\n"
                "Yes = replace\n"
                "No = merge parked lines into this cart\n"
                "Cancel = put ticket back",
                parent=self.winfo_toplevel(),
            )
            if r is None:
                self._parked.insert(idx, ticket)
                return
            if r:
                self._restore_ticket(ticket)
            elif not self._merge_ticket_lines(ticket):
                self._parked.insert(idx, ticket)
                return
        else:
            self._restore_ticket(ticket)
        try:
            self._parked_svc.delete(int(ticket["db_id"]))
        except (KeyError, TypeError, ValueError):
            pass
        self._refresh_parked_from_db()
        try:
            self._search_entry.focus_set()
        except tk.TclError:
            pass

    def refresh(self):
        t = self._sales.get_todays_totals()
        cash = self._sales.get_todays_cash_total()
        if "invoices" in self._kpi_labels:
            self._kpi_labels["invoices"].configure(text=str(t.get("invoice_count", 0)))
        if "gross" in self._kpi_labels:
            self._kpi_labels["gross"].configure(text=format_money(float(t.get("gross_total", 0))))
        if "cash" in self._kpi_labels:
            self._kpi_labels["cash"].configure(text=format_money(cash))
        self._update_kpis_cart_lines()
        self._refresh_parked_from_db()
        try:
            self._search_entry.focus_set()
        except tk.TclError:
            pass
