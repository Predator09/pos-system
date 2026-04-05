"""Reports & CSV exports — Tk / CustomTkinter."""

import tkinter as tk
from datetime import date, timedelta
from tkinter import filedialog

import customtkinter as ctk
import ttkbootstrap as ttk
from ttkbootstrap.constants import LEFT, RIGHT, W, X

from app.services.product_service import ProductService
from app.services.reports_service import ReportsService, format_sales_calendar_day
from app.services.shop_settings import get_display_shop_name
from app.ui.helpers import format_money, show_message
from app.ui.theme_tokens import CTK_TEXT_MUTED


def _first_of_month() -> str:
    t = date.today()
    return t.replace(day=1).isoformat()


def _today() -> str:
    return date.today().isoformat()


def _seven_days_ago() -> str:
    return (date.today() - timedelta(days=6)).isoformat()


class ReportsScreen(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._svc = ReportsService()
        self._products = ProductService()

        self._start_var = tk.StringVar(master=self, value=_first_of_month())
        self._end_var = tk.StringVar(master=self, value=_today())

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill=X, padx=12, pady=8)

        ctk.CTkLabel(outer, text="Reports & analytics", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor=W, pady=(0, 4)
        )
        ctk.CTkLabel(
            outer,
            text="Pick a date range, then open each tab. Exports are UTF-8 CSV.",
            text_color=CTK_TEXT_MUTED,
        ).pack(anchor=W, pady=(0, 10))

        bar = ctk.CTkFrame(outer, fg_color="transparent")
        bar.pack(fill=X, pady=(0, 8))
        ctk.CTkLabel(bar, text="From (YYYY-MM-DD)").pack(side=LEFT, padx=(0, 6))
        ctk.CTkEntry(bar, textvariable=self._start_var, width=120, height=30).pack(side=LEFT, padx=(0, 12))
        ctk.CTkLabel(bar, text="To").pack(side=LEFT, padx=(0, 6))
        ctk.CTkEntry(bar, textvariable=self._end_var, width=120, height=30).pack(side=LEFT, padx=(0, 12))
        ctk.CTkButton(bar, text="Apply range", width=100, command=self.refresh).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(bar, text="This month", width=100, command=self._range_this_month).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(bar, text="Last 7 days", width=100, command=self._range_last_7).pack(side=LEFT)

        self._err = ctk.CTkLabel(outer, text="", text_color="#c1121f")
        self._err.pack(anchor=W, pady=(0, 4))

        nb = ttk.Notebook(outer)
        nb.pack(fill=X, pady=(4, 0))

        # --- Summary ---
        sum_fr = ttk.Frame(nb, padding=8)
        nb.add(sum_fr, text="Summary")
        self._sum_labels: dict[str, ctk.CTkLabel] = {}
        grid = ctk.CTkFrame(sum_fr, fg_color="transparent")
        grid.pack(anchor=W)
        specs = [
            ("invoice_count", "Invoices"),
            ("gross_total", "Gross sales"),
            ("discount_total", "Discounts"),
            ("subtotal_total", "Subtotal (pre-discount)"),
            ("avg_ticket", "Avg ticket (gross)"),
        ]
        for i, (key, title) in enumerate(specs):
            ctk.CTkLabel(grid, text=title + ":", font=ctk.CTkFont(weight="bold")).grid(row=i, column=0, sticky=W, pady=4)
            lb = ctk.CTkLabel(grid, text="—")
            lb.grid(row=i, column=1, sticky=W, padx=(12, 0))
            self._sum_labels[key] = lb

        # --- By day ---
        day_fr = ttk.Frame(nb, padding=8)
        nb.add(day_fr, text="Daily sales")
        self._daily_sales_heading = ctk.CTkLabel(
            day_fr,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._daily_sales_heading.pack(anchor=W, pady=(0, 8))
        self._day_tree = self._make_tree(
            day_fr,
            ("day", "invoices", "gross"),
            ("Calendar day", "Invoices", "Gross"),
            (220, 80, 120),
        )

        # --- Payment ---
        pay_fr = ttk.Frame(nb, padding=8)
        nb.add(pay_fr, text="Payment mix")
        self._pay_tree = self._make_tree(
            pay_fr,
            ("method", "invoices", "gross"),
            ("Method", "Invoices", "Gross"),
            (120, 80, 120),
        )

        # --- Top products ---
        top_fr = ttk.Frame(nb, padding=8)
        nb.add(top_fr, text="Top products")
        self._top_tree = self._make_tree(
            top_fr,
            ("code", "name", "qty", "revenue"),
            ("SKU", "Product", "Qty sold", "Revenue"),
            (100, 220, 90, 110),
        )

        # --- Inventory ---
        inv_fr = ttk.Frame(nb, padding=8)
        nb.add(inv_fr, text="Inventory")
        self._inv_kpi: dict[str, ctk.CTkLabel] = {}
        ig = ctk.CTkFrame(inv_fr, fg_color="transparent")
        ig.pack(anchor=W, pady=(0, 8))
        for i, (key, title) in enumerate(
            (
                ("skus", "Active SKUs"),
                ("units", "Units on hand"),
                ("retail_value", "Retail value"),
                ("cost_value", "Cost value"),
                ("margin_hint", "Retail − cost"),
            )
        ):
            ctk.CTkLabel(ig, text=title + ":", font=ctk.CTkFont(weight="bold")).grid(row=i, column=0, sticky=W, pady=2)
            lb = ctk.CTkLabel(ig, text="—")
            lb.grid(row=i, column=1, sticky=W, padx=(12, 0))
            self._inv_kpi[key] = lb
        ctk.CTkLabel(inv_fr, text="Low stock (≤ min level)", font=ctk.CTkFont(weight="bold")).pack(anchor=W, pady=(8, 4))
        self._low_tree = self._make_tree(
            inv_fr,
            ("code", "name", "stock", "min"),
            ("SKU", "Product", "Stock", "Min"),
            (100, 220, 70, 70),
        )

        # --- Purchases ---
        pur_fr = ttk.Frame(nb, padding=8)
        nb.add(pur_fr, text="Purchases")
        self._pur_tree = self._make_tree(
            pur_fr,
            ("ref", "at", "supplier", "phone", "email", "lines", "value"),
            ("Reference", "Received", "Supplier", "Phone", "Email", "Lines", "Value"),
            (120, 130, 110, 90, 120, 44, 88),
        )

        # --- Export ---
        ex_fr = ttk.Frame(nb, padding=8)
        nb.add(ex_fr, text="Export CSV")
        ctk.CTkLabel(
            ex_fr,
            text="Exports use the date range above.",
            text_color=CTK_TEXT_MUTED,
        ).pack(anchor=W, pady=(0, 12))
        ctk.CTkButton(ex_fr, text="Export sales (one row per invoice)", width=280, command=self._export_sales).pack(
            anchor=W, pady=4
        )
        ctk.CTkButton(ex_fr, text="Export sale lines (one row per line item)", width=280, command=self._export_lines).pack(
            anchor=W, pady=4
        )

    @staticmethod
    def _make_tree(parent, cols: tuple, headings: tuple, widths: tuple):
        wrap = ttk.Frame(parent)
        wrap.pack(fill=X)
        tv = ttk.Treeview(wrap, columns=cols, show="headings", height=14, selectmode="browse")
        for c, h, w in zip(cols, headings, widths):
            tv.heading(c, text=h)
            tv.column(c, width=w)
        sb = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side=LEFT, fill=X)
        sb.pack(side=RIGHT, fill=tk.Y)
        return tv

    def _range_this_month(self) -> None:
        self._start_var.set(_first_of_month())
        self._end_var.set(_today())
        self.refresh()

    def _range_last_7(self) -> None:
        self._start_var.set(_seven_days_ago())
        self._end_var.set(_today())
        self.refresh()

    def _get_range(self) -> tuple[str, str]:
        return self._start_var.get().strip(), self._end_var.get().strip()

    def _clear_err(self) -> None:
        self._err.configure(text="")

    def _set_err(self, msg: str) -> None:
        self._err.configure(text=msg)

    def refresh(self) -> None:
        self._clear_err()
        start, end = self._get_range()
        try:
            summary = self._svc.sales_summary(start, end)
        except ValueError as e:
            self._set_err(str(e))
            return

        self._sum_labels["invoice_count"].configure(text=str(summary["invoice_count"]))
        self._sum_labels["gross_total"].configure(text=format_money(summary["gross_total"]))
        self._sum_labels["discount_total"].configure(text=format_money(summary["discount_total"]))
        self._sum_labels["subtotal_total"].configure(text=format_money(summary["subtotal_total"]))
        self._sum_labels["avg_ticket"].configure(text=format_money(summary["avg_ticket"]))

        self._daily_sales_heading.configure(text=f"Daily sales — {get_display_shop_name()}")

        for tv in (self._day_tree, self._pay_tree, self._top_tree, self._pur_tree, self._low_tree):
            tv.delete(*tv.get_children())

        try:
            for r in self._svc.sales_by_day(start, end):
                self._day_tree.insert(
                    "",
                    tk.END,
                    values=(
                        format_sales_calendar_day(r.get("day")),
                        r.get("invoices"),
                        format_money(float(r.get("gross_total") or 0)),
                    ),
                )
            for r in self._svc.sales_by_payment_method(start, end):
                self._pay_tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.get("method"),
                        r.get("invoices"),
                        format_money(float(r.get("gross_total") or 0)),
                    ),
                )
            for r in self._svc.top_products_by_revenue(start, end, 40):
                q = float(r.get("qty_sold") or 0)
                qv = f"{q:g}" if q == int(q) else f"{q:.2f}"
                self._top_tree.insert(
                    "",
                    tk.END,
                    values=(r.get("code"), r.get("name"), qv, format_money(float(r.get("revenue") or 0))),
                )
            for r in self._svc.purchase_receipts_in_range(start, end):
                self._pur_tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.get("reference"),
                        str(r.get("received_at") or "")[:19],
                        (r.get("supplier_name") or "")[:36],
                        (r.get("supplier_phone") or "")[:28],
                        (r.get("supplier_email") or "")[:36],
                        int(r.get("line_count") or 0),
                        format_money(float(r.get("total_value") or 0)),
                    ),
                )
        except ValueError as e:
            self._set_err(str(e))
            return

        snap = self._svc.inventory_valuation_snapshot()
        self._inv_kpi["skus"].configure(text=str(snap["skus"]))
        self._inv_kpi["units"].configure(text=f"{snap['units']:,.2f}")
        self._inv_kpi["retail_value"].configure(text=format_money(snap["retail_value"]))
        self._inv_kpi["cost_value"].configure(text=format_money(snap["cost_value"]))
        self._inv_kpi["margin_hint"].configure(text=format_money(snap["margin_hint"]))

        for p in self._products.get_low_stock()[:80]:
            self._low_tree.insert(
                "",
                tk.END,
                values=(
                    p.get("code"),
                    p.get("name"),
                    f"{float(p.get('quantity_in_stock') or 0):g}",
                    f"{float(p.get('minimum_stock_level') or 0):g}",
                ),
            )

    def _export_sales(self) -> None:
        start, end = self._get_range()
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"sales_{start}_{end}.csv",
        )
        if not path:
            return
        try:
            out = self._svc.export_sales_csv(path, start, end)
        except ValueError as e:
            show_message(str(e), title="Export", parent=self.winfo_toplevel())
            return
        show_message(f"Saved:\n{out}", title="Export", parent=self.winfo_toplevel())

    def _export_lines(self) -> None:
        start, end = self._get_range()
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"sale_lines_{start}_{end}.csv",
        )
        if not path:
            return
        try:
            out = self._svc.export_sale_lines_csv(path, start, end)
        except ValueError as e:
            show_message(str(e), title="Export", parent=self.winfo_toplevel())
            return
        show_message(f"Saved:\n{out}", title="Export", parent=self.winfo_toplevel())
