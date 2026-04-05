from datetime import date, datetime, timedelta
import tkinter as tk

import customtkinter as ctk
import ttkbootstrap as ttk
from ttkbootstrap.constants import E, EW, LEFT, NW, RIGHT, VERTICAL, W, X, Y

from app.config import APP_NAME, PAD_LG, PAD_MD, PAD_SM, VERSION
from app.services.shop_context import database_path
from app.services.shop_settings import get_display_shop_name
from app.database.connection import db
from app.services.app_settings import AppSettings
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService
from app.services.inventory_service import InventoryService
from app.ui.manage_users_dialog import ManageUsersDialog
from app.ui.dialogs import ReceiptPreviewDialog
from app.services.sales_service import SalesService
from app.ui.helpers import (
    format_money,
    home_welcome_detail_line,
    home_welcome_status_line,
    show_message,
)
from app.ui.theme_tokens import (
    CTK_BTN_GHOST_HOVER,
    CTK_HEADER_ACCENT_TEXT,
    CTK_NAV_BORDER_ACCENT,
    CTK_TEXT_DANGER,
    CTK_TEXT_INFO,
    CTK_TEXT_MUTED,
    CTK_TEXT_SUCCESS,
    TOKENS,
)


class HomeScreen(ttk.Frame):
    """Brikama-style command center: live metrics from SQLite, dark/light appearance toggle."""

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._sales = SalesService()
        self._inventory = InventoryService()
        self._backup = BackupService()

        self._metric_labels = {}
        self._delta_labels = {}
        self._kpi_card_frames = {}
        self._clock_label = None
        self._status_labels = {}
        self._recent_list_frame = None
        self._clock_after_id = None

        self._dark_mode_var = tk.BooleanVar(master=self, value=False)
        self._suppress_appearance_cb = False
        self._appearance_check = None

        self.columnconfigure(0, weight=1)

        self._content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._content_frame.grid(row=0, column=0, sticky="new")
        self._content_frame.columnconfigure(0, weight=1)

        self._build_all_sections()
        self.bind("<Destroy>", self._on_destroy, add=True)
        self._start_clock()
        self._sync_appearance_switch()

    def _on_destroy(self, event):
        if event.widget is self and self._clock_after_id is not None:
            try:
                self.after_cancel(self._clock_after_id)
            except tk.TclError:
                pass
            self._clock_after_id = None

    def _start_clock(self):
        def tick():
            if not self.winfo_exists():
                return
            if self._clock_label is not None:
                try:
                    self._clock_label.configure(text=datetime.now().strftime("%H:%M:%S"))
                except tk.TclError:
                    return
            self._clock_after_id = self.after(1000, tick)

        tick()

    def _sync_appearance_switch(self):
        if self._appearance_check is None:
            return
        dark = AppSettings().get_appearance() == "dark"
        self._suppress_appearance_cb = True
        try:
            self._dark_mode_var.set(dark)
        finally:
            self._suppress_appearance_cb = False

    def _on_appearance_toggle(self):
        if self._suppress_appearance_cb:
            return
        want_dark = self._dark_mode_var.get()
        mode = "dark" if want_dark else "light"
        if hasattr(self.main_window, "apply_appearance"):
            if not self.main_window.apply_appearance(mode):
                show_message("Could not switch appearance.", parent=self.winfo_toplevel())
                self._sync_appearance_switch()
        else:
            self._sync_appearance_switch()

    def _build_all_sections(self):
        self._build_hero_strip()
        self._build_status_strip()
        self._build_main_split()
        self._build_operations_bar()

    def _build_hero_strip(self):
        hero = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        hero.grid(row=0, column=0, sticky=EW, padx=PAD_LG, pady=(PAD_LG, PAD_MD))
        hero.columnconfigure(1, weight=1)

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.grid(row=0, column=0, sticky=W)

        ctk.CTkLabel(
            left,
            text=get_display_shop_name(),
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text=f"{APP_NAME} · GMD · offline-first · semantic UI palette",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=CTK_TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        mid = ctk.CTkFrame(hero, fg_color="transparent")
        mid.grid(row=0, column=1, sticky=W, padx=(PAD_LG, 0))

        self._welcome_label = ctk.CTkLabel(
            mid,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            wraplength=520,
            justify="left",
        )
        self._welcome_label.pack(anchor="w")

        self._role_badge = ctk.CTkLabel(
            mid,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("white", "white"),
            fg_color=("gray35", "gray25"),
            corner_radius=8,
            padx=10,
            pady=4,
        )
        self._role_badge.pack(anchor="w", pady=(6, 0))

        right = ctk.CTkFrame(hero, fg_color="transparent")
        right.grid(row=0, column=2, sticky=E)

        toggle_row = ctk.CTkFrame(right, fg_color="transparent")
        toggle_row.pack(anchor="e", fill=X, pady=(0, PAD_SM))

        ctk.CTkLabel(
            toggle_row,
            text="Dark mode",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=CTK_TEXT_MUTED,
        ).pack(side=RIGHT, padx=(PAD_SM, 0))

        self._appearance_check = ctk.CTkCheckBox(
            toggle_row,
            text="",
            checkbox_width=22,
            checkbox_height=22,
            variable=self._dark_mode_var,
            command=self._on_appearance_toggle,
        )
        self._appearance_check.pack(side=RIGHT)

        ctk.CTkLabel(
            right,
            text=date.today().strftime("%A, %d %B %Y"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=CTK_TEXT_MUTED,
        ).pack(anchor="e")

        self._clock_label = ctk.CTkLabel(
            right,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=CTK_TEXT_INFO,
        )
        self._clock_label.pack(anchor="e", pady=(4, 0))

        ctk.CTkLabel(
            right,
            text=f"v{VERSION}",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=CTK_TEXT_MUTED,
        ).pack(anchor="e", pady=(2, 0))

    def _build_status_strip(self):
        strip = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        strip.grid(row=1, column=0, sticky=EW, padx=PAD_LG, pady=(0, PAD_MD))

        inner = ctk.CTkFrame(strip, fg_color=("gray92", "gray22"), corner_radius=10)
        inner.pack(fill=X, padx=0, pady=0)
        ip = ctk.CTkFrame(inner, fg_color="transparent")
        ip.pack(fill=X, padx=PAD_MD, pady=PAD_SM)

        self._status_labels["db"] = ctk.CTkLabel(ip, text="", font=ctk.CTkFont(family="Segoe UI", size=11))
        self._status_labels["db"].pack(side=LEFT, padx=(0, PAD_LG))

        ttk.Separator(ip, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=PAD_SM, pady=2)

        self._status_labels["theme"] = ctk.CTkLabel(
            ip,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=CTK_TEXT_MUTED,
        )
        self._status_labels["theme"].pack(side=LEFT, padx=(PAD_LG, 0))

        ttk.Separator(ip, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=PAD_SM, pady=2)

        self._status_labels["backup"] = ctk.CTkLabel(
            ip,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=CTK_TEXT_MUTED,
        )
        self._status_labels["backup"].pack(side=LEFT, padx=(PAD_LG, 0))

    def _build_main_split(self):
        main = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        main.grid(row=2, column=0, sticky="new", padx=PAD_LG, pady=(0, PAD_LG))
        main.columnconfigure(0, weight=2)
        main.columnconfigure(1, weight=1)

        left = ctk.CTkFrame(main, fg_color="transparent")
        left.grid(row=0, column=0, sticky="new", padx=(0, PAD_MD))
        left.columnconfigure(0, weight=1)

        self._build_kpi_section(left)
        self._build_recent_activity(left)

        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="new")
        right.columnconfigure(0, weight=1)

        self._build_session_card(right)

    def _build_kpi_section(self, parent):
        wrap = ttk.Labelframe(
            parent,
            text="Shop metrics (live · SQLite)",
            bootstyle="primary",
            padding=PAD_MD,
        )
        wrap.grid(row=0, column=0, sticky=EW, pady=(0, PAD_MD))
        for c in range(3):
            wrap.columnconfigure(c, weight=1)

        specs = [
            ("today_gross", 0, 0, "Today's sales", "Total collected · no tax", "primary"),
            ("invoice_count", 0, 1, "Invoices today", "Completed checkouts", "success"),
            ("low_under_10", 0, 2, "Low stock", "Under 10 units", "warning"),
            ("inventory", 1, 0, "Total inventory", "Active products", "info"),
            ("cash_today", 1, 1, "Cash (today)", "CASH tenders today", "secondary"),
        ]
        for key, gr, gc, title, hint, style in specs:
            val, delta, border = self._kpi_tile(wrap, gr, gc, title, hint, style)
            self._metric_labels[key] = val
            self._delta_labels[key] = delta
            self._kpi_card_frames[key] = border

    def _kpi_tile(self, parent, grid_row, grid_col, title, hint, bootstyle):
        padx_r = (0, PAD_SM) if grid_col < 2 else (0, 0)
        card = ctk.CTkFrame(parent, fg_color="transparent")
        card.grid(row=grid_row, column=grid_col, sticky="new", padx=padx_r, pady=(0, PAD_SM))

        border = ttk.Labelframe(
            card,
            text=title,
            bootstyle=bootstyle,
            padding=(PAD_MD, PAD_SM),
        )
        border.pack(fill=X)

        value = ctk.CTkLabel(border, text="—", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        value.pack(anchor="w")

        delta = ctk.CTkLabel(
            border,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=CTK_TEXT_MUTED,
        )
        delta.pack(anchor="w", pady=(2, 0))

        ctk.CTkLabel(
            border,
            text=hint,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=CTK_TEXT_MUTED,
        ).pack(anchor="w", pady=(4, 0))

        return value, delta, border

    def _build_recent_activity(self, parent):
        box = ttk.Labelframe(
            parent,
            text="Recent checkouts (last 5)",
            bootstyle="secondary",
            padding=PAD_MD,
        )
        box.grid(row=1, column=0, sticky="new")
        box.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            box,
            text="Click a row to preview the receipt.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=CTK_TEXT_MUTED,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self._recent_list_frame = ctk.CTkFrame(box, fg_color="transparent")
        self._recent_list_frame.grid(row=1, column=0, sticky="new")

    def _build_session_card(self, parent):
        card = ttk.Labelframe(
            parent,
            text="This session",
            bootstyle="secondary",
            padding=PAD_MD,
        )
        card.pack(fill=X)

        self._app_info_inner = ctk.CTkFrame(card, fg_color="transparent")
        self._app_info_inner.pack(fill=X)

    def _build_operations_bar(self):
        foot = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        foot.grid(row=3, column=0, sticky=EW, padx=PAD_LG, pady=(0, PAD_LG))
        foot.columnconfigure(3, weight=1)

        ctk.CTkButton(
            foot,
            text="Backup now",
            width=120,
            fg_color=("#E8A317", "#B87D0A"),
            hover_color=("#D49412", "#9A6A08"),
            command=self._backup_now,
        ).grid(row=0, column=0, sticky=W)

        self._manage_users_btn = ctk.CTkButton(
            foot,
            text="Manage users",
            width=120,
            command=self._open_manage_users,
        )
        self._manage_users_btn.grid(row=0, column=1, sticky=W, padx=(PAD_MD, 0))

        ctk.CTkButton(
            foot,
            text="Refresh dashboard",
            width=140,
            fg_color="transparent",
            border_width=2,
            border_color=CTK_NAV_BORDER_ACCENT,
            text_color=CTK_HEADER_ACCENT_TEXT,
            hover_color=CTK_BTN_GHOST_HOVER,
            command=self.refresh,
        ).grid(row=0, column=2, sticky=W, padx=(PAD_MD, 0))

        self._footer_hint = ctk.CTkLabel(
            foot,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=CTK_TEXT_MUTED,
        )
        self._footer_hint.grid(row=0, column=3, sticky=E)

    def _rebuild_recent_list(self, sales_rows):
        for w in self._recent_list_frame.winfo_children():
            w.destroy()
        rows = sales_rows[:5]
        if not rows:
            ctk.CTkLabel(
                self._recent_list_frame,
                text="No checkouts yet — record a sale in Point of Sale.",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=CTK_TEXT_MUTED,
                wraplength=520,
            ).grid(row=0, column=0, sticky="w", padx=PAD_SM, pady=PAD_SM)
            return

        for i, sale in enumerate(rows):
            row_f = ctk.CTkFrame(self._recent_list_frame, fg_color="transparent")
            row_f.grid(row=i, column=0, sticky=EW, pady=(0, 4))
            row_f.columnconfigure(1, weight=1)
            try:
                sid = int(sale.get("id"))
            except (TypeError, ValueError):
                continue

            inv = sale.get("invoice_number") or f"Order #{sale.get('id')}"
            total = float(sale.get("total_amount") or 0)
            pay = (sale.get("payment_method") or "—").upper()

            la = ctk.CTkLabel(
                row_f,
                text=inv,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                anchor="w",
            )
            la.grid(row=0, column=0, sticky="w")

            lb = ctk.CTkLabel(
                row_f,
                text=format_money(total),
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=CTK_TEXT_SUCCESS,
            )
            lb.grid(row=0, column=1, sticky="w", padx=(PAD_MD, 0))

            lc = ctk.CTkLabel(
                row_f,
                text=pay,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=CTK_TEXT_MUTED,
            )
            lc.grid(row=0, column=2, sticky="e")

            for w in (row_f, la, lb, lc):
                w.bind("<Button-1>", lambda e, s=sid: self._preview_recent_checkout(s))
                try:
                    w.configure(cursor="hand2")
                except tk.TclError:
                    pass

        self._recent_list_frame.columnconfigure(0, weight=1)

    def _preview_recent_checkout(self, sale_id: int) -> None:
        full = self._sales.get_sale(int(sale_id))
        if not full:
            show_message("That sale could not be loaded.", title="Receipt", parent=self.winfo_toplevel())
            return
        ReceiptPreviewDialog(self.main_window, full)

    def _open_manage_users(self):
        if not AuthService.is_owner(getattr(self.main_window, "current_user", None)):
            return
        ManageUsersDialog(self.winfo_toplevel(), self.main_window)

    def _backup_now(self):
        try:
            path = self._backup.create_full_backup()
            self._footer_hint.configure(text="Backup completed")
            show_message(
                f"Backup saved to:\n{path}",
                title="Backup Complete",
                parent=self.winfo_toplevel(),
            )
            self._update_status_strip()
        except Exception as e:
            show_message(
                f"Backup failed: {e}",
                title="Backup Error",
                parent=self.winfo_toplevel(),
            )

    @staticmethod
    def _short_path(path: str, max_len: int = 42) -> str:
        p = str(path)
        if len(p) <= max_len:
            return p
        return "…" + p[-(max_len - 1) :]

    @staticmethod
    def _format_delta(today_n: float, yest_n: float, *, money: bool = False) -> str:
        diff = today_n - yest_n
        if yest_n == 0 and today_n == 0:
            return "Same as yesterday"
        if yest_n == 0:
            return "Up from zero yesterday" if today_n > 0 else "No change"
        pct = (diff / yest_n) * 100.0 if yest_n else 0.0
        arrow = "↑" if diff >= 0 else "↓"
        if money:
            return f"{arrow} {format_money(abs(diff))} vs yday ({pct:+.0f}%)"
        return f"{arrow} {abs(int(diff))} vs yday ({pct:+.0f}%)"

    def _yesterday_totals(self) -> tuple[float, int]:
        y = (date.today() - timedelta(days=1)).isoformat()
        rows = self._sales.get_sales_by_date(y, y)
        gross = sum(float(r.get("total_amount") or 0) for r in rows)
        return gross, len(rows)

    def _latest_backup_text(self) -> str:
        d = self._backup.backup_dir
        if not d.exists():
            return "Backups: folder missing"
        files = list(d.glob("backup_*.json"))
        if not files:
            return "Backups: none yet"
        latest = max(files, key=lambda p: p.stat().st_mtime)
        return f"Latest backup: {latest.name}"

    def _sync_manage_users_button(self):
        btn = getattr(self, "_manage_users_btn", None)
        if btn is None:
            return
        if AuthService.is_owner(getattr(self.main_window, "current_user", None)):
            btn.grid()
        else:
            btn.grid_remove()

    def _update_welcome_and_info(self):
        u = getattr(self.main_window, "current_user", None) or {}
        shop = get_display_shop_name()
        self._welcome_label.configure(text=home_welcome_detail_line(u, shop))

        role = (u.get("role") or "staff").title()
        self._role_badge.configure(text=f"  {role}  ")

        for w in self._app_info_inner.winfo_children():
            w.destroy()

        db_display = self._short_path(str(database_path()))
        info_rows = [
            ("App", f"{APP_NAME} v{VERSION}"),
            ("Database", db_display),
            ("User", u.get("username", "—")),
            ("Role", role),
            ("Brand primary", TOKENS.PRIMARY),
        ]

        for i, (label, value) in enumerate(info_rows):
            ctk.CTkLabel(
                self._app_info_inner,
                text=f"{label}:",
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=CTK_TEXT_MUTED,
            ).grid(row=i, column=0, sticky=NW, padx=(0, 10), pady=3)

            ctk.CTkLabel(
                self._app_info_inner,
                text=str(value),
                font=ctk.CTkFont(family="Segoe UI", size=11),
                wraplength=220,
            ).grid(row=i, column=1, sticky=NW, pady=3)

    def _update_status_strip(self):
        try:
            db.fetchone("SELECT 1")
            self._status_labels["db"].configure(text="● Database online", text_color=CTK_TEXT_SUCCESS)
        except Exception:
            self._status_labels["db"].configure(text="● Database issue", text_color=CTK_TEXT_DANGER)

        u = getattr(self.main_window, "current_user", None) or {}
        self._status_labels["theme"].configure(
            text=home_welcome_status_line(u, get_display_shop_name()),
        )

        self._status_labels["backup"].configure(text=self._latest_backup_text())

    def refresh(self):
        self._update_welcome_and_info()
        self._sync_manage_users_button()
        self._update_status_strip()
        self._sync_appearance_switch()

        try:
            today_totals = self._sales.get_todays_totals()
            y_gross, y_inv = self._yesterday_totals()

            self._metric_labels["today_gross"].configure(text=format_money(today_totals["gross_total"]))
            self._delta_labels["today_gross"].configure(
                text=self._format_delta(today_totals["gross_total"], y_gross, money=True),
            )

            self._metric_labels["invoice_count"].configure(text=str(today_totals["invoice_count"]))
            self._delta_labels["invoice_count"].configure(
                text=self._format_delta(today_totals["invoice_count"], y_inv, money=False),
            )

            low_n = self._inventory.get_low_stock_count(10)
            self._metric_labels["low_under_10"].configure(text=f"{low_n} items")
            self._delta_labels["low_under_10"].configure(
                text="Reorder soon" if low_n else "Stock levels OK",
            )
            frame = self._kpi_card_frames.get("low_under_10")
            if frame is not None:
                frame.config(bootstyle="warning" if low_n else "secondary")

            inv_n = self._inventory.get_active_product_count()
            self._metric_labels["inventory"].configure(text=f"{inv_n} SKUs")
            self._delta_labels["inventory"].configure(text="Active in catalog")

            cash = self._sales.get_todays_cash_total()
            self._metric_labels["cash_today"].configure(text=format_money(cash))
            self._delta_labels["cash_today"].configure(text="CASH payments today")

            recent = self._sales.get_recent_sales(5)
            self._rebuild_recent_list(recent)

            self._footer_hint.configure(text="Dashboard updated")
        except Exception as e:
            for key in self._metric_labels:
                self._metric_labels[key].configure(text="—")
                self._delta_labels[key].configure(text="")
            self._footer_hint.configure(text=f"Could not load stats: {str(e)[:48]}")
