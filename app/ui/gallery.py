"""Product gallery — images and prices, sorted by best-selling (units sold)."""

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import ttkbootstrap as ttk
from PIL import Image, ImageTk
from ttkbootstrap.constants import LEFT, W, X

from app.services.product_service import ProductService
from app.ui.helpers import format_money
from app.ui.products import ProductEditorDialog
from app.ui.theme_tokens import CTK_TEXT_DANGER, CTK_TEXT_MUTED, CTK_TEXT_WARN


_THUMB = 132


def _load_thumbnail(path: str, master, max_size: int = _THUMB) -> ImageTk.PhotoImage | None:
    try:
        p = Path(path)
        if not p.is_file():
            return None
        img = Image.open(p).convert("RGB")
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img, master=master)
    except OSError:
        return None


class GalleryScreen(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._svc = ProductService()
        self._photos: list[ImageTk.PhotoImage] = []
        self._search_var = ctk.StringVar(master=self)
        self._cat_var = ctk.StringVar(master=self, value="(all)")

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill=X, padx=12, pady=8)

        ctk.CTkLabel(outer, text="Gallery", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor=W, pady=(0, 4))
        ctk.CTkLabel(
            outer,
            text=(
                "Best sellers first. Add products here or in Inventory. "
                "Click image to set photo · double-click name to edit (stock, expiry, QC) · "
                "click price to add to sale (qty 1)."
            ),
            text_color=CTK_TEXT_MUTED,
            wraplength=920,
            justify="left",
        ).pack(anchor=W, pady=(0, 10))

        bar = ctk.CTkFrame(outer, fg_color="transparent")
        bar.pack(fill=X, pady=(0, 8))
        ctk.CTkButton(
            bar,
            text="Add product",
            width=120,
            command=self._add_product,
        ).pack(side=LEFT, padx=(0, 8))
        ctk.CTkButton(
            bar,
            text="Products & inventory",
            width=160,
            fg_color="transparent",
            border_width=1,
            command=self._open_products,
        ).pack(side=LEFT, padx=(0, 16))
        ctk.CTkLabel(bar, text="Search").pack(side=LEFT, padx=(0, 6))
        se = ctk.CTkEntry(bar, textvariable=self._search_var, width=200, height=30)
        se.pack(side=LEFT, padx=(0, 12))
        se.bind("<Return>", lambda e: self.refresh())
        ctk.CTkLabel(bar, text="Category").pack(side=LEFT, padx=(0, 6))
        self._cat_combo = ctk.CTkComboBox(bar, variable=self._cat_var, width=180, height=30, values=["(all)"])
        self._cat_combo.pack(side=LEFT, padx=(0, 12))
        ctk.CTkButton(bar, text="Apply", width=88, command=self.refresh).pack(side=LEFT)

        self._grid_host = ctk.CTkFrame(outer, fg_color="transparent")
        self._grid_host.pack(fill=X)
        self._cols = 4

    def _add_price_to_sales(self, product_id: int) -> None:
        mw = self.main_window
        if hasattr(mw, "add_product_to_sales_cart"):
            mw.add_product_to_sales_cart(product_id, 1.0)

    def _cross_refresh_products(self) -> None:
        pr = self.main_window.screens.get("products")
        if pr is not None and hasattr(pr, "refresh"):
            try:
                pr.refresh()
            except Exception:
                pass

    def _add_product(self) -> None:
        cats = self._svc.list_categories()
        d = ProductEditorDialog(self.winfo_toplevel(), self._svc, None, cats)
        if d.saved:
            self._cross_refresh_products()
            self.refresh()

    def _open_products(self) -> None:
        self.main_window.show_screen("products")

    def _edit_product(self, product_id: int) -> None:
        cats = self._svc.list_categories()
        d = ProductEditorDialog(self.winfo_toplevel(), self._svc, product_id, cats)
        if d.saved:
            self._cross_refresh_products()
            self.refresh()

    def _pick_image_for_product(self, product_id: int) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Product image",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.webp *.bmp"),
                ("All", "*.*"),
            ],
        )
        if not path:
            return
        try:
            self._svc.set_product_image_from_file(product_id, path)
        except Exception as e:
            messagebox.showerror("Image", str(e), parent=self.winfo_toplevel())
            return
        self._cross_refresh_products()
        self.refresh()

    @staticmethod
    def _stock_caption(product: dict) -> tuple[str, tuple[str, str]]:
        qty = float(product.get("quantity_in_stock") or 0)
        min_l = float(product.get("minimum_stock_level") or 0)
        qtxt = str(int(qty)) if qty == int(qty) else f"{qty:.1f}"
        if qty <= 0:
            return f"Stock: {qtxt} · Out", CTK_TEXT_DANGER
        if qty <= min_l:
            return f"Stock: {qtxt} · Low", CTK_TEXT_WARN
        return f"Stock: {qtxt}", CTK_TEXT_MUTED

    def refresh(self) -> None:
        self._photos.clear()
        for w in self._grid_host.winfo_children():
            w.destroy()

        cats = ["(all)"] + self._svc.list_categories()
        cur = self._cat_var.get()
        self._cat_combo.configure(values=cats)
        if cur not in cats:
            self._cat_var.set("(all)")

        try:
            rows = self._svc.list_active_products_by_units_sold(
                search=self._search_var.get().strip() or None,
                category=None if self._cat_var.get() == "(all)" else self._cat_var.get(),
                limit=240,
            )
        except Exception:
            rows = []

        if not rows:
            ctk.CTkLabel(self._grid_host, text="No products match your filters.", text_color=CTK_TEXT_MUTED).grid(
                row=0, column=0, padx=8, pady=24
            )
            return

        for col in range(self._cols):
            self._grid_host.grid_columnconfigure(col, weight=1)

        for idx, p in enumerate(rows):
            r, c = divmod(idx, self._cols)
            pid = int(p["id"])
            card = ctk.CTkFrame(self._grid_host, corner_radius=10, border_width=1, fg_color=("gray95", "gray22"))
            card.grid(row=r, column=c, padx=8, pady=8, sticky="n")

            ipath = (p.get("image_path") or "").strip()
            ph = _load_thumbnail(ipath, self) if ipath else None
            if ph:
                self._photos.append(ph)
                img_lbl = ctk.CTkLabel(card, text="", image=ph, width=_THUMB, height=_THUMB, cursor="hand2")
            else:
                img_lbl = ctk.CTkLabel(
                    card,
                    text="No image\n(click)",
                    width=_THUMB,
                    height=_THUMB,
                    fg_color=("gray85", "gray30"),
                    corner_radius=8,
                    text_color=CTK_TEXT_MUTED,
                    cursor="hand2",
                )
            img_lbl.pack(padx=10, pady=(10, 6))
            img_lbl.bind("<Button-1>", lambda e, i=pid: self._pick_image_for_product(i))

            name = (p.get("name") or "")[:36]
            nl = ctk.CTkLabel(
                card,
                text=name or "—",
                font=ctk.CTkFont(size=12),
                wraplength=140,
                cursor="hand2",
            )
            nl.pack(padx=8)
            nl.bind("<Double-Button-1>", lambda e, i=pid: self._edit_product(i))

            st_txt, st_col = self._stock_caption(p)
            ctk.CTkLabel(card, text=st_txt, font=ctk.CTkFont(size=11), text_color=st_col).pack(padx=8, pady=(2, 0))

            price_lbl = ctk.CTkLabel(
                card,
                text=format_money(float(p.get("selling_price") or 0)),
                font=ctk.CTkFont(size=14, weight="bold"),
                cursor="hand2",
            )
            price_lbl.pack(padx=8, pady=(2, 0))
            price_lbl.bind("<Button-1>", lambda e, i=pid: self._add_price_to_sales(i))

            us = float(p.get("units_sold") or 0)
            us_txt = f"{int(us)} sold" if us == int(us) else f"{us:.1f} sold"
            ctk.CTkLabel(card, text=us_txt, font=ctk.CTkFont(size=11), text_color=CTK_TEXT_MUTED).pack(
                padx=8, pady=(0, 10)
            )
