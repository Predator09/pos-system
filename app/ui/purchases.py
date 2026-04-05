"""Purchases (supplier stock) — Tk / CustomTkinter."""

import tkinter as tk

import customtkinter as ctk
import ttkbootstrap as ttk
from ttkbootstrap.constants import LEFT, RIGHT, W, X

from app.services.product_service import ProductService
from app.services.purchase_service import PurchaseService
from app.services.supplier_service import SupplierService
from app.ui.dialogs import PickProductDialog
from app.ui.supplier_editor_dialog import SupplierEditorDialog
from app.ui.helpers import format_money, show_message
from app.ui.theme_tokens import CTK_TEXT_MUTED


class PurchaseScreen(ttk.Frame):
    """Record purchases from suppliers: lines, supplier, weighted-average cost option, history."""

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._products = ProductService()
        self._purchases = PurchaseService()
        self._suppliers = SupplierService()
        self._lines: list[dict] = []
        self._pending_product: dict | None = None
        self._linked_supplier_id: int | None = None
        self._suppress_supplier_combo = False
        self._filling_supplier_fields = False
        self._supplier_combo_ids: list[int | None] = []

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill=X, padx=12, pady=8)

        ctk.CTkLabel(outer, text="Purchases", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor=W, pady=(0, 4)
        )
        ctk.CTkLabel(
            outer,
            text="Add lines, then click Purchase. Stock increases immediately; cost can follow weighted average.",
            text_color=CTK_TEXT_MUTED,
        ).pack(anchor=W, pady=(0, 12))

        dir_lf = ttk.Labelframe(
            outer,
            text="Registered suppliers (for future reference & quick fill)",
            bootstyle="secondary",
            padding=8,
        )
        dir_lf.pack(fill=X, pady=(0, 10))
        dir_inner = ctk.CTkFrame(dir_lf, fg_color="transparent")
        dir_inner.pack(fill=X)
        s_cols = ("name", "phone", "email")
        self._supplier_tree = ttk.Treeview(
            dir_inner, columns=s_cols, show="headings", height=5, selectmode="browse"
        )
        self._supplier_tree.heading("name", text="Name")
        self._supplier_tree.heading("phone", text="Phone")
        self._supplier_tree.heading("email", text="Email")
        self._supplier_tree.column("name", width=200)
        self._supplier_tree.column("phone", width=120)
        self._supplier_tree.column("email", width=200)
        ssb = ttk.Scrollbar(dir_inner, orient=tk.VERTICAL, command=self._supplier_tree.yview)
        self._supplier_tree.configure(yscrollcommand=ssb.set)
        self._supplier_tree.pack(side=tk.LEFT, fill=X, expand=True)
        ssb.pack(side=tk.RIGHT, fill=tk.Y)
        self._supplier_tree.bind("<Double-1>", lambda e: self._apply_selected_supplier_to_form())

        dir_btns = ctk.CTkFrame(dir_lf, fg_color="transparent")
        dir_btns.pack(fill=X, pady=(8, 0))
        ctk.CTkButton(dir_btns, text="New supplier", width=110, command=self._new_supplier).pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkButton(dir_btns, text="Edit selected", width=110, fg_color="transparent", border_width=1, command=self._edit_supplier).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ctk.CTkButton(dir_btns, text="Use for this receipt", width=140, command=self._apply_selected_supplier_to_form).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ctk.CTkButton(dir_btns, text="Refresh list", width=100, fg_color="transparent", border_width=1, command=self._reload_supplier_directory).pack(
            side=tk.LEFT
        )

        hdr = ctk.CTkFrame(outer, fg_color="transparent")
        hdr.pack(fill=X, pady=(0, 8))
        ctk.CTkLabel(hdr, text="Quick pick").grid(row=0, column=0, sticky=W, padx=(0, 8))
        self._supplier_combo = ctk.CTkComboBox(
            hdr,
            values=["— Type below or pick from list —"],
            width=320,
            height=32,
            state="readonly",
            command=self._on_supplier_combo,
        )
        self._supplier_combo.grid(row=0, column=1, sticky=W)
        ctk.CTkLabel(hdr, text="Supplier (this receipt)").grid(row=1, column=0, sticky=W, pady=(8, 0), padx=(0, 8))
        self._supplier_var = tk.StringVar(master=self)
        self._supplier_var.trace_add("write", self._on_supplier_field_edited)
        ctk.CTkEntry(hdr, textvariable=self._supplier_var, width=280, height=32).grid(row=1, column=1, sticky=W, pady=(8, 0))

        ctk.CTkLabel(hdr, text="Phone").grid(row=2, column=0, sticky=W, pady=(8, 0), padx=(0, 8))
        self._supplier_phone_var = tk.StringVar(master=self)
        self._supplier_phone_var.trace_add("write", self._on_supplier_field_edited)
        ctk.CTkEntry(hdr, textvariable=self._supplier_phone_var, width=280, height=32).grid(
            row=2, column=1, sticky=W, pady=(8, 0)
        )

        ctk.CTkLabel(hdr, text="Email").grid(row=3, column=0, sticky=W, pady=(8, 0), padx=(0, 8))
        self._supplier_email_var = tk.StringVar(master=self)
        self._supplier_email_var.trace_add("write", self._on_supplier_field_edited)
        ctk.CTkEntry(hdr, textvariable=self._supplier_email_var, width=280, height=32).grid(
            row=3, column=1, sticky=W, pady=(8, 0)
        )

        self._wac_var = tk.BooleanVar(master=self, value=True)
        ctk.CTkCheckBox(
            hdr,
            text="Update product cost (weighted average with existing stock)",
            variable=self._wac_var,
        ).grid(row=4, column=1, sticky=W, pady=(8, 0))

        line_fr = ctk.CTkFrame(outer, fg_color="transparent")
        line_fr.pack(fill=X, pady=(0, 8))
        ctk.CTkLabel(line_fr, text="Qty").pack(side=LEFT, padx=(0, 6))
        self._qty_var = tk.StringVar(master=self, value="1")
        ctk.CTkEntry(line_fr, textvariable=self._qty_var, width=72, height=32).pack(side=LEFT, padx=(0, 12))
        ctk.CTkLabel(line_fr, text="Unit cost (GMD)").pack(side=LEFT, padx=(0, 6))
        self._cost_var = tk.StringVar(master=self, value="")
        ctk.CTkEntry(line_fr, textvariable=self._cost_var, width=100, height=32).pack(side=LEFT, padx=(0, 12))
        ctk.CTkButton(line_fr, text="Pick product…", width=120, command=self._pick_product).pack(
            side=LEFT, padx=(0, 8)
        )
        ctk.CTkButton(line_fr, text="Add line", width=100, command=self._add_line).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(line_fr, text="Remove selected", width=130, fg_color="transparent", border_width=1, command=self._remove_line).pack(
            side=LEFT
        )

        tree_fr = ttk.Frame(outer)
        tree_fr.pack(fill=X, pady=(0, 8))
        cols = ("code", "name", "qty", "ucost", "total")
        self._tree = ttk.Treeview(tree_fr, columns=cols, show="headings", height=8, selectmode="browse")
        self._tree.heading("code", text="Product code")
        self._tree.heading("name", text="Product")
        self._tree.heading("qty", text="Qty")
        self._tree.heading("ucost", text="Unit cost")
        self._tree.heading("total", text="Line total")
        self._tree.column("code", width=100)
        self._tree.column("name", width=220)
        self._tree.column("qty", width=70)
        self._tree.column("ucost", width=90)
        self._tree.column("total", width=100)
        sb = ttk.Scrollbar(tree_fr, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side=LEFT, fill=X)
        sb.pack(side=RIGHT, fill=tk.Y)

        act = ctk.CTkFrame(outer, fg_color="transparent")
        act.pack(fill=X, pady=(0, 12))
        ctk.CTkButton(act, text="Purchase", width=120, command=self._post_receipt).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(
            act,
            text="Clear draft",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._clear_draft,
        ).pack(side=LEFT)
        self._draft_total = ctk.CTkLabel(act, text="Draft total: " + format_money(0))
        self._draft_total.pack(side=RIGHT)

        ctk.CTkLabel(outer, text="Recent purchases", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor=W, pady=(4, 4))
        hist_fr = ttk.Frame(outer)
        hist_fr.pack(fill=X)
        hcols = ("ref", "at", "supplier", "phone", "email", "lines", "value")
        self._hist = ttk.Treeview(hist_fr, columns=hcols, show="headings", height=6, selectmode="browse")
        for c, t, w in (
            ("ref", "Reference", 140),
            ("at", "Received", 130),
            ("supplier", "Supplier", 120),
            ("phone", "Phone", 100),
            ("email", "Email", 140),
            ("lines", "Lines", 44),
            ("value", "Value", 90),
        ):
            self._hist.heading(c, text=t)
            self._hist.column(c, width=w)
        hsb = ttk.Scrollbar(hist_fr, orient=tk.VERTICAL, command=self._hist.yview)
        self._hist.configure(yscrollcommand=hsb.set)
        self._hist.pack(side=LEFT, fill=X)
        hsb.pack(side=RIGHT, fill=tk.Y)

        self._reload_supplier_directory()

    def _on_supplier_field_edited(self, *_args) -> None:
        if self._filling_supplier_fields:
            return
        self._linked_supplier_id = None
        self._set_supplier_combo_manual()

    def _set_supplier_combo_manual(self) -> None:
        self._suppress_supplier_combo = True
        try:
            self._supplier_combo.set("— Type below or pick from list —")
        finally:
            self._suppress_supplier_combo = False

    def _on_supplier_combo(self, choice: str) -> None:
        if self._suppress_supplier_combo:
            return
        labels = list(self._supplier_combo.cget("values"))
        try:
            idx = labels.index(choice)
        except ValueError:
            return
        if idx <= 0 or idx >= len(self._supplier_combo_ids):
            self._linked_supplier_id = None
            return
        sid = self._supplier_combo_ids[idx]
        if sid is None:
            self._linked_supplier_id = None
            return
        row = self._suppliers.get(int(sid))
        if not row:
            self._reload_supplier_directory()
            return
        self._filling_supplier_fields = True
        try:
            self._supplier_var.set(row.get("name") or "")
            self._supplier_phone_var.set(row.get("phone") or "")
            self._supplier_email_var.set(row.get("email") or "")
        finally:
            self._filling_supplier_fields = False
        self._linked_supplier_id = int(sid)

    def _reload_supplier_directory(self) -> None:
        self._supplier_tree.delete(*self._supplier_tree.get_children())
        rows = self._suppliers.list_active()
        for r in rows:
            self._supplier_tree.insert(
                "",
                tk.END,
                iid=str(r["id"]),
                values=(
                    (r.get("name") or "")[:48],
                    (r.get("phone") or "")[:28],
                    (r.get("email") or "")[:36],
                ),
            )
        labels: list[str] = ["— Type below or pick from list —"]
        ids: list[int | None] = [None]
        for r in rows:
            nm = (r.get("name") or "").strip() or f"#{r['id']}"
            extra = []
            if r.get("phone"):
                extra.append(str(r["phone"])[:16])
            lab = f"{nm} ({', '.join(extra)})" if extra else nm
            labels.append(lab[:72])
            ids.append(int(r["id"]))
        self._supplier_combo_ids = ids
        self._suppress_supplier_combo = True
        try:
            self._supplier_combo.configure(values=labels)
            self._supplier_combo.set(labels[0])
        finally:
            self._suppress_supplier_combo = False
        self._linked_supplier_id = None

    def _selected_supplier_id_from_tree(self) -> int | None:
        sel = self._supplier_tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except (TypeError, ValueError):
            return None

    def _new_supplier(self) -> None:
        d = SupplierEditorDialog(self.winfo_toplevel(), self._suppliers, None)
        self.wait_window(d)
        if getattr(d, "saved", False):
            self._reload_supplier_directory()

    def _edit_supplier(self) -> None:
        sid = self._selected_supplier_id_from_tree()
        if sid is None:
            show_message("Select a supplier in the list first.", parent=self.winfo_toplevel())
            return
        d = SupplierEditorDialog(self.winfo_toplevel(), self._suppliers, sid)
        self.wait_window(d)
        if getattr(d, "saved", False):
            self._reload_supplier_directory()

    def _apply_selected_supplier_to_form(self) -> None:
        sid = self._selected_supplier_id_from_tree()
        if sid is None:
            show_message("Select a supplier in the list first.", parent=self.winfo_toplevel())
            return
        row = self._suppliers.get(sid)
        if not row:
            self._reload_supplier_directory()
            return
        labels = list(self._supplier_combo.cget("values"))
        try:
            idx = self._supplier_combo_ids.index(sid)
        except ValueError:
            idx = -1
        self._suppress_supplier_combo = True
        try:
            if 0 <= idx < len(labels):
                self._supplier_combo.set(labels[idx])
        finally:
            self._suppress_supplier_combo = False
        self._filling_supplier_fields = True
        try:
            self._supplier_var.set(row.get("name") or "")
            self._supplier_phone_var.set(row.get("phone") or "")
            self._supplier_email_var.set(row.get("email") or "")
        finally:
            self._filling_supplier_fields = False
        self._linked_supplier_id = sid

    def _pick_product(self) -> None:
        d = PickProductDialog(self.winfo_toplevel(), self._products)
        if d.result:
            self._pending_product = d.result
            c = float(d.result.get("cost_price") or 0)
            self._cost_var.set(str(c) if c else "")

    def _add_line(self) -> None:
        if self._pending_product:
            p = self._pending_product
            self._pending_product = None
        else:
            d = PickProductDialog(self.winfo_toplevel(), self._products)
            if not d.result:
                return
            p = d.result
        pid = int(p["id"])
        try:
            qty = float(str(self._qty_var.get()).replace(",", "").strip() or "0")
        except ValueError:
            show_message("Enter a valid quantity.", parent=self.winfo_toplevel())
            return
        if qty <= 0:
            show_message("Quantity must be greater than zero.", parent=self.winfo_toplevel())
            return
        raw = self._cost_var.get().strip().replace(",", "")
        if not raw:
            uc = float(p.get("cost_price") or 0)
        else:
            try:
                uc = float(raw)
            except ValueError:
                show_message("Enter a valid unit cost.", parent=self.winfo_toplevel())
                return
        if uc < 0:
            show_message("Unit cost cannot be negative.", parent=self.winfo_toplevel())
            return
        lt = round(qty * uc, 2)
        self._lines.append(
            {
                "product_id": pid,
                "code": p.get("code") or "",
                "name": p.get("name") or "",
                "quantity": qty,
                "unit_cost": uc,
                "line_total": lt,
            }
        )
        self._refresh_tree()
        self._qty_var.set("1")

    def _remove_line(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        iid = sel[0]
        try:
            idx = self._tree.index(iid)
        except tk.TclError:
            return
        if 0 <= idx < len(self._lines):
            del self._lines[idx]
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        self._tree.delete(*self._tree.get_children())
        total = 0.0
        for row in self._lines:
            total += float(row["line_total"])
            self._tree.insert(
                "",
                tk.END,
                values=(
                    row["code"],
                    row["name"],
                    f"{row['quantity']:g}" if row["quantity"] == int(row["quantity"]) else f"{row['quantity']:.2f}",
                    format_money(row["unit_cost"]),
                    format_money(row["line_total"]),
                ),
            )
        self._draft_total.configure(text="Draft total: " + format_money(total))

    def _clear_draft(self) -> None:
        self._lines.clear()
        self._refresh_tree()
        self._filling_supplier_fields = True
        try:
            self._supplier_var.set("")
            self._supplier_phone_var.set("")
            self._supplier_email_var.set("")
        finally:
            self._filling_supplier_fields = False
        self._linked_supplier_id = None
        self._set_supplier_combo_manual()

    def _post_receipt(self) -> None:
        if not self._lines:
            show_message("Add at least one line before purchasing.", parent=self.winfo_toplevel())
            return
        try:
            result = self._purchases.receive_receipt(
                [
                    {"product_id": x["product_id"], "quantity": x["quantity"], "unit_cost": x["unit_cost"]}
                    for x in self._lines
                ],
                supplier_name=self._supplier_var.get().strip() or None,
                supplier_phone=self._supplier_phone_var.get().strip() or None,
                supplier_email=self._supplier_email_var.get().strip() or None,
                supplier_id=self._linked_supplier_id,
                update_average_cost=bool(self._wac_var.get()),
            )
        except ValueError as e:
            show_message(str(e), parent=self.winfo_toplevel())
            return
        except Exception as e:
            show_message(f"Could not complete purchase: {e}", parent=self.winfo_toplevel())
            return
        show_message(
            f"Purchase recorded — {result['reference']}\n{result['line_count']} line(s) · {format_money(result['total_value'])}",
            parent=self.winfo_toplevel(),
        )
        self._clear_draft()
        self.refresh()

    def refresh(self) -> None:
        self._hist.delete(*self._hist.get_children())
        for r in self._purchases.list_recent_receipts(40):
            self._hist.insert(
                "",
                tk.END,
                values=(
                    r.get("reference") or "",
                    str(r.get("received_at") or "")[:19],
                    (r.get("supplier_name") or "")[:36],
                    (r.get("supplier_phone") or "")[:28],
                    (r.get("supplier_email") or "")[:36],
                    int(r.get("line_count") or 0),
                    format_money(float(r.get("total_value") or 0)),
                ),
            )
