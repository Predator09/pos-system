"""Inventory dashboard: filters, table, bulk ops, CSV, product editor."""

from __future__ import annotations

import csv
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk
import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, EW, LEFT, RIGHT, VERTICAL, W, X

from app.config import PAD_LG, PAD_MD, PAD_SM
from app.services.app_settings import AppSettings
from app.services.product_service import ProductService
from app.ui.helpers import format_money, show_message
from app.ui.theme_tokens import (
    CTK_TEXT_MUTED,
    PRODUCT_ROW_EXPIRED_BG,
    PRODUCT_ROW_EXPIRED_FG,
    PRODUCT_ROW_INACTIVE_BG,
    PRODUCT_ROW_INACTIVE_FG,
    product_active_row_surface,
)

_TREE_COLS = ("id", "name", "category", "price", "stock", "cost", "live", "status", "expiry")
_CSV_FIELDS = [
    "id",
    "code",
    "name",
    "category",
    "cost_price",
    "selling_price",
    "quantity_in_stock",
    "minimum_stock_level",
    "is_active",
    "expiry_date",
    "image_path",
    "description",
]


def _norm_csv_key(k: str) -> str:
    return (k or "").strip().lower().replace(" ", "_")


def _csv_row_to_payload(row: dict) -> dict:
    m = {_norm_csv_key(k): (v or "").strip() if isinstance(v, str) else v for k, v in row.items()}
    if "code" not in m and m.get("sku"):
        m["code"] = m["sku"]
    return m


class ProductEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, service: ProductService, product_id: int | None, categories: list[str]):
        super().__init__(parent)
        self.service = service
        self.product_id = product_id
        self.saved = False
        self.title("Product" if product_id else "New product")
        self.geometry("520x560")
        self.minsize(480, 520)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill=BOTH, expand=True, padx=PAD_MD, pady=PAD_MD)

        # Do not use self._name — Tk stores the widget's internal name there.
        self._name_var = tk.StringVar(master=self)
        self._category = tk.StringVar(master=self)
        self._code = tk.StringVar(master=self)
        self._price = tk.StringVar(master=self, value="0")
        self._cost = tk.StringVar(master=self, value="0")
        self._stock = tk.StringVar(master=self, value="0")
        self._min_alert = tk.StringVar(master=self, value="10")
        self._status = tk.StringVar(master=self, value="active")
        self._expiry = tk.StringVar(master=self)
        self._image = tk.StringVar(master=self)
        self._desc = tk.StringVar(master=self)

        row = 0
        for label, var, width in (
            ("Name", self._name_var, 42),
            ("Category", None, 0),
            ("SKU / Code", self._code, 24),
            ("Selling price (GMD)", self._price, 16),
            ("Cost (GMD)", self._cost, 16),
            ("Stock qty", self._stock, 12),
            ("Min alert level", self._min_alert, 12),
            ("Status", None, 0),
            ("Expiry (YYYY-MM-DD)", self._expiry, 16),
            ("Image path", None, 0),
            ("Description", self._desc, 42),
        ):
            ctk.CTkLabel(body, text=label + ":").grid(row=row, column=0, sticky=W, pady=2)
            if var is not None:
                ctk.CTkEntry(body, textvariable=var, width=max(280, width * 8)).grid(
                    row=row, column=1, sticky=EW, pady=2, padx=(PAD_SM, 0)
                )
            elif label == "Category":
                self._cat_combo = ctk.CTkComboBox(
                    body,
                    variable=self._category,
                    values=[""] + categories,
                    width=280,
                )
                self._cat_combo.grid(row=row, column=1, sticky=EW, pady=2, padx=(PAD_SM, 0))
            elif label == "Status":
                ctk.CTkComboBox(
                    body,
                    variable=self._status,
                    values=("active", "inactive"),
                    width=260,
                    state="readonly",
                ).grid(row=row, column=1, sticky=W, pady=2, padx=(PAD_SM, 0))
            else:
                img_row = ctk.CTkFrame(body, fg_color="transparent")
                img_row.grid(row=row, column=1, sticky=EW, pady=2, padx=(PAD_SM, 0))
                ctk.CTkEntry(img_row, textvariable=self._image, width=200).pack(side=LEFT, fill=X, expand=True)
                ctk.CTkButton(img_row, text="Browse…", width=88, fg_color="transparent", border_width=1, command=self._browse_image).pack(
                    side=LEFT, padx=(PAD_SM, 0)
                )
            row += 1

        body.columnconfigure(1, weight=1)

        if product_id:
            p = service.get_product(product_id)
            if p:
                self._name_var.set(p.get("name") or "")
                self._category.set(p.get("category") or "")
                self._code.set(p.get("code") or "")
                self._price.set(str(p.get("selling_price") or 0))
                self._cost.set(str(p.get("cost_price") or 0))
                self._stock.set(str(p.get("quantity_in_stock") or 0))
                self._min_alert.set(str(p.get("minimum_stock_level") or 10))
                self._status.set("active" if p.get("is_active") else "inactive")
                self._expiry.set((p.get("expiry_date") or "") or "")
                self._image.set((p.get("image_path") or "") or "")
                self._desc.set(p.get("description") or "")
            ctk.CTkLabel(body, text="Code is unique; changing SKU may break links.", text_color=CTK_TEXT_MUTED).grid(
                row=row, column=0, columnspan=2, sticky=W, pady=(PAD_SM, 0)
            )
            row += 1

        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.pack(fill=X, padx=PAD_MD, pady=(0, PAD_MD))
        ctk.CTkButton(btn, text="Save", command=self._save).pack(side=RIGHT, padx=(PAD_SM, 0))
        ctk.CTkButton(btn, text="Cancel", fg_color="transparent", border_width=1, command=self._cancel).pack(side=RIGHT)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda e: self._cancel())
        self.wait_visibility(self)
        self.wait_window(self)

    def _browse_image(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Product image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.webp"), ("All", "*.*")],
        )
        if path:
            self._image.set(path)

    def _parse_float(self, s: str, label: str) -> float:
        try:
            return float(str(s).strip().replace(",", ""))
        except ValueError as e:
            raise ValueError(f"{label}: invalid number") from e

    def _save(self):
        name = self._name_var.get().strip()
        code = self._code.get().strip()
        if not name or not code:
            show_message("Name and SKU are required.", parent=self)
            return
        try:
            price = self._parse_float(self._price.get(), "Price")
            cost = self._parse_float(self._cost.get(), "Cost")
            stock = self._parse_float(self._stock.get(), "Stock")
            min_a = self._parse_float(self._min_alert.get(), "Min alert")
        except ValueError as e:
            show_message(str(e), parent=self)
            return
        exp = self._expiry.get().strip()
        if exp and len(exp) != 10:
            show_message("Use expiry format YYYY-MM-DD or leave blank.", parent=self)
            return
        is_active = 1 if self._status.get() == "active" else 0
        img = self._image.get().strip() or None
        desc = self._desc.get().strip() or None
        cat = self._category.get().strip() or None
        try:
            if self.product_id:
                self.service.update_product(
                    self.product_id,
                    name=name,
                    code=code,
                    category=cat,
                    description=desc,
                    cost_price=cost,
                    selling_price=price,
                    quantity_in_stock=stock,
                    minimum_stock_level=min_a,
                    is_active=is_active,
                    expiry_date=exp or None,
                    image_path=img,
                )
            else:
                if self.service.get_product_by_code(code):
                    show_message("That SKU already exists.", parent=self)
                    return
                self.service.create_product(
                    name,
                    code,
                    cost,
                    price,
                    category=cat,
                    description=desc,
                    quantity_in_stock=stock,
                    minimum_stock_level=min_a,
                    is_active=bool(is_active),
                    expiry_date=exp or None,
                    image_path=img,
                )
        except Exception as e:
            show_message(f"Save failed: {e}", parent=self)
            return
        self.saved = True
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.grab_release()
        self.destroy()


class ProductsScreen(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._svc = ProductService()
        self._all_products: list[dict] = []
        self._stat_labels: dict[str, ctk.CTkLabel] = {}
        self._tree: ttk.Treeview | None = None
        self._bulk_frame: ttk.Frame | None = None
        self._ctx_menu: tk.Menu | None = None
        self._ctx_iid: str | None = None

        self.columnconfigure(0, weight=1)

        self._search_var = tk.StringVar(master=self)
        self._search_var.trace_add("write", lambda *_a: self._schedule_filter())
        self._cat_var = tk.StringVar(master=self, value="(all)")
        self._status_var = tk.StringVar(master=self, value="(all)")
        self._stock_var = tk.StringVar(master=self, value="(all)")
        self._pmin_var = tk.StringVar(master=self)
        self._pmax_var = tk.StringVar(master=self)

        self._filter_after: str | None = None

        self._build_ui()
        self.bind("<Destroy>", self._on_destroy, add=True)

    def _on_destroy(self, event):
        if event.widget is not self:
            return
        if self._filter_after is not None:
            try:
                self.after_cancel(self._filter_after)
            except tk.TclError:
                pass
            self._filter_after = None

    def _schedule_filter(self):
        if self._filter_after is not None:
            try:
                self.after_cancel(self._filter_after)
            except tk.TclError:
                pass
        self._filter_after = self.after(180, self._apply_filters)

    def _build_ui(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky=EW, padx=PAD_LG, pady=(PAD_MD, PAD_SM))
        head.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            head,
            text="Products & inventory",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=("#000000", "#f1f5f9"),
        ).grid(row=0, column=0, sticky=W)
        hint = ctk.CTkLabel(
            head,
            text="Insert new · F2 edit · Del deactivate · right-click row for +1 / −1",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=CTK_TEXT_MUTED,
        )
        hint.grid(row=1, column=0, columnspan=3, sticky=W, pady=(4, 0))

        btns = ctk.CTkFrame(head, fg_color="transparent")
        btns.grid(row=0, column=2, rowspan=2, sticky="e")
        ctk.CTkButton(btns, text="New product", command=self._new_product).pack(side=RIGHT, padx=(PAD_SM, 0))
        ctk.CTkButton(btns, text="Import CSV", width=100, fg_color="transparent", border_width=1, command=self._import_csv).pack(
            side=RIGHT, padx=(PAD_SM, 0)
        )
        ctk.CTkButton(btns, text="Export CSV", width=100, fg_color="transparent", border_width=1, command=self._export_csv).pack(
            side=RIGHT
        )

        self._build_stats_row()

        filt = ttk.Labelframe(self, text="Search & filters", bootstyle="secondary", padding=PAD_MD)
        filt.grid(row=2, column=0, sticky=EW, padx=PAD_LG, pady=(0, PAD_SM))
        for c in range(8):
            filt.columnconfigure(c, weight=1 if c in (1, 3, 5) else 0)

        ctk.CTkLabel(filt, text="Name").grid(row=0, column=0, sticky=W)
        ctk.CTkEntry(filt, textvariable=self._search_var, width=140).grid(row=1, column=0, sticky=EW, padx=(0, PAD_SM))

        ctk.CTkLabel(filt, text="Category").grid(row=0, column=1, sticky=W)
        self._cat_combo = ctk.CTkComboBox(
            filt,
            variable=self._cat_var,
            values=["(all)"],
            width=130,
            state="readonly",
            command=lambda _v: self._apply_filters(),
        )
        self._cat_combo.grid(row=1, column=1, sticky=EW, padx=(0, PAD_SM))

        ctk.CTkLabel(filt, text="Price min").grid(row=0, column=2, sticky=W)
        ctk.CTkEntry(filt, textvariable=self._pmin_var, width=88).grid(row=1, column=2, sticky=W, padx=(0, PAD_SM))
        ctk.CTkLabel(filt, text="Price max").grid(row=0, column=3, sticky=W)
        ctk.CTkEntry(filt, textvariable=self._pmax_var, width=88).grid(row=1, column=3, sticky=W, padx=(0, PAD_SM))

        ctk.CTkLabel(filt, text="Stock level").grid(row=0, column=4, sticky=W)
        stock_cb = ctk.CTkComboBox(
            filt,
            variable=self._stock_var,
            values=["(all)", "low", "out", "ok"],
            width=110,
            state="readonly",
            command=lambda _v: self._apply_filters(),
        )
        stock_cb.grid(row=1, column=4, sticky=W, padx=(0, PAD_SM))

        ctk.CTkLabel(filt, text="Status").grid(row=0, column=5, sticky=W)
        st_cb = ctk.CTkComboBox(
            filt,
            variable=self._status_var,
            values=["(all)", "active", "inactive", "expired"],
            width=120,
            state="readonly",
            command=lambda _v: self._apply_filters(),
        )
        st_cb.grid(row=1, column=5, sticky=W, padx=(0, PAD_SM))

        ctk.CTkButton(filt, text="Apply", width=88, command=self._apply_filters).grid(row=1, column=6, sticky=W, padx=(PAD_MD, 0))
        ctk.CTkButton(filt, text="Clear", width=80, fg_color="transparent", border_width=1, command=self._clear_filters).grid(
            row=1, column=7, sticky=W, padx=(PAD_SM, 0)
        )

        self._bulk_frame = ttk.Labelframe(
            self,
            text="Bulk actions (selected rows)",
            bootstyle="warning",
            padding=PAD_MD,
        )
        self._bulk_frame.grid(row=3, column=0, sticky=EW, padx=PAD_LG, pady=(0, PAD_SM))
        self._bulk_frame.grid_remove()
        bf = ctk.CTkFrame(self._bulk_frame, fg_color="transparent")
        bf.pack(fill=X)
        ctk.CTkLabel(bf, text="Selection:").pack(side=LEFT)
        self._sel_count = ctk.CTkLabel(bf, text="0", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        self._sel_count.pack(side=LEFT, padx=(4, PAD_LG))
        ctk.CTkButton(bf, text="Restock +5 each", command=lambda: self._bulk_restock(5)).pack(side=LEFT, padx=(0, PAD_SM))
        ctk.CTkButton(
            bf,
            text="Deactivate",
            fg_color=("#C1121F", "#9A0E18"),
            hover_color=("#A00F1A", "#7D0C14"),
            command=self._bulk_deactivate,
        ).pack(side=LEFT, padx=(0, PAD_SM))
        ctk.CTkButton(bf, text="Price +/- %", width=100, fg_color="transparent", border_width=1, command=self._bulk_price_pct).pack(
            side=LEFT, padx=(0, PAD_SM)
        )
        ctk.CTkButton(bf, text="Set min alert", width=110, fg_color="transparent", border_width=1, command=self._bulk_min_alert).pack(
            side=LEFT
        )

        table_wrap = ctk.CTkFrame(self, fg_color="transparent")
        table_wrap.grid(row=4, column=0, sticky="new", padx=PAD_LG, pady=(0, PAD_LG))
        table_wrap.columnconfigure(0, weight=1)

        scroll_y = ttk.Scrollbar(table_wrap, orient=VERTICAL)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self._tree = ttk.Treeview(
            table_wrap,
            columns=_TREE_COLS,
            show="headings",
            selectmode="extended",
            yscrollcommand=scroll_y.set,
            height=18,
        )
        scroll_y.config(command=self._tree.yview)
        self._tree.grid(row=0, column=0, sticky="new")

        headings = {
            "id": ("ID", 48),
            "name": ("Name", 200),
            "category": ("Category", 100),
            "price": ("Price", 88),
            "stock": ("Stock", 64),
            "cost": ("Cost", 88),
            "live": ("Live value", 96),
            "status": ("Status", 80),
            "expiry": ("Expiry", 96),
        }
        for col, (title, w) in headings.items():
            self._tree.heading(col, text=title)
            self._tree.column(col, width=w, anchor=W if col == "name" else "center")

        self._configure_inventory_tree_tags()

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda e: self._edit_selected())
        self._tree.bind("<Button-3>", self._on_tree_right_click)
        self.bind("<Insert>", self._global_insert)
        self._tree.bind("<Insert>", self._global_insert)
        self._tree.bind("<F2>", lambda e: self._edit_selected())
        self._tree.bind("<Delete>", lambda e: self._delete_selected())

        self._build_ctx_menu()

    def _configure_inventory_tree_tags(self) -> None:
        if self._tree is None:
            return
        _sf = ("Segoe UI", 10, "bold")
        abg, afg = product_active_row_surface(AppSettings().get_appearance())
        self._tree.tag_configure("active_ok", background=abg, foreground=afg, font=_sf)
        self._tree.tag_configure("low", background="#5c4510", foreground="#fde68a", font=_sf)
        self._tree.tag_configure("bad", background="#5c1f1f", foreground="#fde68a", font=_sf)
        self._tree.tag_configure(
            "inactive",
            background=PRODUCT_ROW_INACTIVE_BG,
            foreground=PRODUCT_ROW_INACTIVE_FG,
            font=_sf,
        )
        self._tree.tag_configure(
            "expired",
            background=PRODUCT_ROW_EXPIRED_BG,
            foreground=PRODUCT_ROW_EXPIRED_FG,
            font=_sf,
        )

    def apply_theme_tokens(self) -> None:
        """Re-apply Treeview row colors when light/dark appearance changes."""
        self._configure_inventory_tree_tags()

    def _build_stats_row(self):
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.grid(row=1, column=0, sticky=EW, padx=PAD_LG, pady=PAD_SM)
        for c in range(6):
            box.columnconfigure(c, weight=1)

        specs = [
            ("total", "Total products", "secondary"),
            ("low", "Low stock", "warning"),
            ("out", "Out of stock", "danger"),
            ("value", "Inventory value", "secondary"),
            ("topcat", "Top-selling category", "info"),
            ("avg", "Avg. price (active)", "secondary"),
        ]
        _title_font = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        _stat_value_color = ("#000000", "#f1f5f9")
        for i, (key, title, style) in enumerate(specs):
            lf = ttk.Labelframe(box, text=title, bootstyle=style, padding=(PAD_SM, PAD_SM))
            if key == "avg":
                lf.configure(text="")
                title_row = ctk.CTkFrame(lf, fg_color="transparent")
                title_row.pack(anchor="w", fill=X)
                ctk.CTkLabel(title_row, text="Avg. price (", font=_title_font, text_color=_stat_value_color).pack(side=LEFT)
                ctk.CTkLabel(title_row, text="active", font=_title_font, text_color=_stat_value_color).pack(side=LEFT)
                ctk.CTkLabel(title_row, text=")", font=_title_font, text_color=_stat_value_color).pack(side=LEFT)
            lf.grid(row=0, column=i, sticky="new", padx=(0, PAD_SM) if i < 5 else (0, 0))
            lab = ctk.CTkLabel(
                lf,
                text="—",
                font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
                text_color=_stat_value_color,
            )
            lab.pack(anchor="w")
            self._stat_labels[key] = lab

    def _build_ctx_menu(self):
        self._ctx_menu = tk.Menu(self, tearoff=0)
        self._ctx_menu.add_command(label="Add 1 stock", command=lambda: self._ctx_adjust(1))
        self._ctx_menu.add_command(label="Sell 1 unit", command=lambda: self._ctx_adjust(-1))
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="Edit…", command=self._edit_selected)
        self._ctx_menu.add_command(label="Deactivate", command=self._delete_selected)

    def _global_insert(self, event):
        w = self.focus_get()
        if isinstance(w, (ttk.Entry, tk.Entry, tk.Text, ctk.CTkEntry)):
            return
        self._new_product()
        return "break"

    def _on_tree_right_click(self, event):
        if not self._tree or not self._ctx_menu:
            return
        row = self._tree.identify_row(event.y)
        if not row:
            return
        if row not in self._tree.selection():
            self._tree.selection_set(row)
        self._ctx_iid = row
        try:
            self._ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._ctx_menu.grab_release()

    def _ctx_adjust(self, delta: float):
        iid = self._ctx_iid
        if not iid or not self._tree:
            return
        try:
            pid = int(iid)
        except ValueError:
            return
        p = self._svc.get_product(pid)
        if not p:
            return
        if delta < 0 and float(p.get("quantity_in_stock") or 0) < 1:
            show_message("No stock to sell.", parent=self.winfo_toplevel())
            return
        self._svc.adjust_stock_delta(pid, delta)
        self.refresh()

    def _on_select(self, _evt=None):
        if not self._tree or not self._bulk_frame:
            return
        n = len(self._tree.selection())
        self._sel_count.configure(text=str(n))
        if n:
            self._bulk_frame.grid()
        else:
            self._bulk_frame.grid_remove()

    def _selected_ids(self) -> list[int]:
        if not self._tree:
            return []
        out = []
        for iid in self._tree.selection():
            try:
                out.append(int(iid))
            except ValueError:
                continue
        return out

    def _clear_filters(self):
        self._search_var.set("")
        self._cat_var.set("(all)")
        self._status_var.set("(all)")
        self._stock_var.set("(all)")
        self._pmin_var.set("")
        self._pmax_var.set("")
        self._apply_filters()

    def _parse_opt_float(self, s: str) -> float | None:
        t = str(s).strip().replace(",", "")
        if not t:
            return None
        try:
            return float(t)
        except ValueError:
            return None

    def _passes_filters(self, p: dict) -> bool:
        q = self._search_var.get().strip().lower()
        if q and q not in (p.get("name") or "").lower() and q not in (p.get("code") or "").lower():
            return False
        cat = self._cat_var.get()
        if cat and cat != "(all)":
            if (p.get("category") or "") != cat:
                return False
        pmin = self._parse_opt_float(self._pmin_var.get())
        pmax = self._parse_opt_float(self._pmax_var.get())
        price = float(p.get("selling_price") or 0)
        if pmin is not None and price < pmin:
            return False
        if pmax is not None and price > pmax:
            return False
        st = ProductService.row_status(p)
        fs = self._status_var.get()
        if fs and fs != "(all)" and st != fs:
            return False
        sk = self._stock_var.get()
        if sk and sk != "(all)":
            qty = float(p.get("quantity_in_stock") or 0)
            mn = float(p.get("minimum_stock_level") or 0)
            active = bool(p.get("is_active"))
            if sk == "low":
                if not active or qty <= 0 or qty > mn:
                    return False
            elif sk == "out":
                if not active or qty > 0:
                    return False
            elif sk == "ok":
                if not active or qty <= 0 or qty <= mn:
                    return False
        return True

    def _row_tag(self, p: dict) -> str:
        return ProductService.inventory_row_tag(p)

    def _status_label(self, p: dict) -> str:
        st = ProductService.row_status(p)
        if st == "active":
            return "Active"
        if st == "inactive":
            return "Inactive"
        return "Expired"

    def _apply_filters(self):
        if self._filter_after is not None:
            try:
                self.after_cancel(self._filter_after)
            except tk.TclError:
                pass
            self._filter_after = None
        if not self._tree:
            return
        for item in self._tree.get_children():
            self._tree.delete(item)
        for p in self._all_products:
            if not self._passes_filters(p):
                continue
            pid = int(p["id"])
            qty = float(p.get("quantity_in_stock") or 0)
            price = float(p.get("selling_price") or 0)
            live = qty * price
            exp = (p.get("expiry_date") or "") or "—"
            self._tree.insert(
                "",
                tk.END,
                iid=str(pid),
                values=(
                    pid,
                    p.get("name") or "",
                    p.get("category") or "—",
                    format_money(price),
                    f"{qty:g}" if qty == int(qty) else f"{qty:.2f}",
                    format_money(float(p.get("cost_price") or 0)),
                    format_money(live),
                    self._status_label(p),
                    exp,
                ),
                tags=(self._row_tag(p),),
            )
        self._on_select()

    def _update_stats(self):
        s = self._svc.get_inventory_dashboard_stats()
        self._stat_labels["total"].configure(text=str(s["total_products"]))
        self._stat_labels["low"].configure(text=str(s["low_stock"]))
        self._stat_labels["out"].configure(text=str(s["out_of_stock"]))
        self._stat_labels["value"].configure(text=format_money(s["inventory_value"]))
        self._stat_labels["topcat"].configure(text=s["top_category"] or "—")
        self._stat_labels["avg"].configure(text=format_money(s["avg_price"]))

    def _refresh_category_combo(self):
        cats = ["(all)"] + self._svc.list_categories()
        self._cat_combo.configure(values=cats)
        if self._cat_var.get() not in cats:
            self._cat_var.set("(all)")

    def refresh(self):
        self._all_products = self._svc.list_all_products()
        self._refresh_category_combo()
        self._update_stats()
        self._apply_filters()

    def _new_product(self):
        cats = self._svc.list_categories()
        d = ProductEditorDialog(self.winfo_toplevel(), self._svc, None, cats)
        if d.saved:
            self.refresh()

    def _edit_selected(self):
        ids = self._selected_ids()
        if len(ids) != 1:
            show_message("Select one product to edit.", parent=self.winfo_toplevel())
            return
        cats = self._svc.list_categories()
        d = ProductEditorDialog(self.winfo_toplevel(), self._svc, ids[0], cats)
        if d.saved:
            self.refresh()

    def _delete_selected(self):
        ids = self._selected_ids()
        if not ids:
            show_message("Select at least one product.", parent=self.winfo_toplevel())
            return
        if not messagebox.askyesno(
            "Deactivate",
            f"Mark {len(ids)} product(s) as inactive?",
            parent=self.winfo_toplevel(),
        ):
            return
        self._svc.bulk_deactivate(ids)
        self.refresh()

    def _bulk_restock(self, n: float):
        ids = self._selected_ids()
        if not ids:
            return
        self._svc.bulk_add_stock(ids, n)
        self.refresh()

    def _bulk_deactivate(self):
        self._delete_selected()

    def _bulk_price_pct(self):
        ids = self._selected_ids()
        if not ids:
            return
        v = simpledialog.askfloat(
            "Price adjustment",
            "Percent change (e.g. 10 for +10%, -5 for -5%):",
            parent=self.winfo_toplevel(),
        )
        if v is None:
            return
        self._svc.bulk_adjust_selling_price_percent(ids, v)
        self.refresh()

    def _bulk_min_alert(self):
        ids = self._selected_ids()
        if not ids:
            return
        v = simpledialog.askfloat(
            "Minimum stock alert",
            "New minimum level for all selected:",
            parent=self.winfo_toplevel(),
        )
        if v is None:
            return
        self._svc.bulk_set_minimum_stock(ids, v)
        self.refresh()

    def _export_csv(self):
        rows = [p for p in self._all_products if self._passes_filters(p)]
        if not rows:
            show_message("No rows to export (adjust filters).", parent=self.winfo_toplevel())
            return
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Export products",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=_CSV_FIELDS, extrasaction="ignore")
                w.writeheader()
                for p in rows:
                    w.writerow(
                        {
                            "id": p.get("id"),
                            "code": p.get("code"),
                            "name": p.get("name"),
                            "category": p.get("category") or "",
                            "cost_price": p.get("cost_price"),
                            "selling_price": p.get("selling_price"),
                            "quantity_in_stock": p.get("quantity_in_stock"),
                            "minimum_stock_level": p.get("minimum_stock_level"),
                            "is_active": 1 if p.get("is_active") else 0,
                            "expiry_date": p.get("expiry_date") or "",
                            "image_path": p.get("image_path") or "",
                            "description": p.get("description") or "",
                        }
                    )
        except OSError as e:
            show_message(f"Export failed: {e}", parent=self.winfo_toplevel())
            return
        show_message(f"Exported {len(rows)} row(s).", parent=self.winfo_toplevel())

    def _import_csv(self):
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
            title="Import products",
        )
        if not path:
            return
        n_ins = n_up = n_err = 0
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                r = csv.DictReader(f)
                if not r.fieldnames:
                    show_message("CSV has no header row.", parent=self.winfo_toplevel())
                    return
                for raw in r:
                    payload = _csv_row_to_payload(raw)
                    try:
                        kind, _ = self._svc.upsert_product_from_row(payload)
                        if kind == "insert":
                            n_ins += 1
                        else:
                            n_up += 1
                    except Exception:
                        n_err += 1
        except OSError as e:
            show_message(f"Import failed: {e}", parent=self.winfo_toplevel())
            return
        self.refresh()
        show_message(
            f"Import done. Added {n_ins}, updated {n_up}, skipped/errors {n_err}.",
            parent=self.winfo_toplevel(),
        )
