from app.tkinter_ctk_compat import apply_customtkinter_tkinter_shim

apply_customtkinter_tkinter_shim()

import tkinter as tk
from pathlib import Path

import customtkinter as ctk
import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, E, LEFT, NSEW, RIGHT, TOP, W, X

from app.config import WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH, format_app_footer_text
from app.services.app_settings import (
    AppSettings,
    THEME_DARK,
    THEME_LIGHT,
    resolve_startup_theme,
    theme_for_appearance,
)
from app.database.connection import db
from app.database.migrations import DatabaseMigrations
from app.services.backup_service import BackupService
from app.ui.home import HomeScreen
from app.ui.login_screen import LoginScreen
from app.ui.products import ProductsScreen
from app.ui.purchases import PurchaseScreen
from app.ui.gallery import GalleryScreen
from app.ui.reports import ReportsScreen
from app.ui.sales import SaleScreen
from app.ui.motion_tk import stagger_nav_button_entrance
from app.ui.profile_dialog import ProfileDialog
from app.ui.theme_tokens import (
    CTK_HEADER_ACCENT_TEXT,
    CTK_NAV_BORDER_ACCENT,
    CTK_NAV_BORDER_MUTED,
    CTK_NAV_BORDER_SALES,
    CTK_NAV_HOVER_SURFACE,
    CTK_NAV_SALES_HOVER,
    CTK_NAV_SALES_SELECTED,
    CTK_NAV_SELECTED_FG,
    CTK_NAV_SELECTED_HOVER,
    CTK_NAV_TEXT_MUTED,
    CTK_TEXT_MUTED,
    TOKENS,
)

_POS_SURFACE_THEME = Path(__file__).resolve().parent.parent / "themes" / "pos_surface.json"
from app.ui.widgets.shop_logo import ShopLogoWidget


_SCREEN_SPECS = (
    (HomeScreen, "home"),
    (ProductsScreen, "products"),
    (GalleryScreen, "gallery"),
    (SaleScreen, "sales"),
    (PurchaseScreen, "purchases"),
    (ReportsScreen, "reports"),
)


class MainWindow(ttk.Window):
    def __init__(self):
        # hdpi=False: Windows per-monitor DPI + Tk can break title-bar move/resize hit-testing.
        super().__init__(
            title=WINDOW_TITLE,
            themename=resolve_startup_theme(),
            size=(WINDOW_WIDTH, WINDOW_HEIGHT),
            resizable=(True, True),
            minsize=(960, 540),
            hdpi=False,
        )
        if _POS_SURFACE_THEME.is_file():
            ctk.set_default_color_theme(str(_POS_SURFACE_THEME))
        else:
            ctk.set_default_color_theme("dark-blue")
        ctk.set_appearance_mode("Dark" if AppSettings().get_appearance() == "dark" else "Light")
        self._pin_default_root_for_image_assets()
        self.current_user = None
        self._header_user_label = None
        self.screens = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._current_screen_name: str | None = None
        self._main_canvas: tk.Canvas | None = None
        self._scrollable_inner: ctk.CTkFrame | None = None
        self._canvas_window: int | None = None
        self._main_vsb: ctk.CTkScrollbar | None = None

        migrations = DatabaseMigrations(db)
        migrations.init_database()
        db.connect()

        self._content = ttk.Frame(self)
        self._content.pack(fill=BOTH, expand=True)

        self._show_login()
        self.center_window()

    def _show_login(self):
        self._unbind_main_scroll_wheel()
        self._main_canvas = None
        self._scrollable_inner = None
        self._canvas_window = None
        self._main_vsb = None
        self.current_user = None
        for w in self._content.winfo_children():
            w.destroy()
        LoginScreen(self._content, self).pack(fill=BOTH, expand=True)

    def enter_app(self, user: dict):
        self.current_user = user
        for w in self._content.winfo_children():
            w.destroy()
        self.update_idletasks()

        backup = BackupService()
        backup.auto_backup_daily()

        self._build_main_shell()
        self.show_screen("home")
        stagger_nav_button_entrance(
            self,
            self._nav_buttons,
            ["home", "products", "gallery", "sales", "purchases", "reports"],
        )
        # Do not re-center here — keeps the window where the user left it after login.

    def refresh_header_user_display(self):
        u = self.current_user or {}
        role = (u.get("role") or "staff").title()
        lab = getattr(self, "_header_user_label", None)
        if lab is not None:
            try:
                if lab.winfo_exists():
                    lab.configure(text=f"{u.get('full_name', '')}  ·  {role}")
            except tk.TclError:
                pass

    def _open_my_profile(self):
        ProfileDialog(self, self)

    def _build_main_shell(self):
        top_frame = ctk.CTkFrame(self._content, fg_color="transparent")
        top_frame.pack(fill=X, padx=12, pady=(8, 4))
        top_frame.columnconfigure(1, weight=1)

        logo_wrap = ctk.CTkFrame(top_frame, fg_color="transparent")
        logo_wrap.grid(row=0, column=0, sticky=W)
        self._header_logo = ShopLogoWidget(logo_wrap, size=52, editable=True)
        self._header_logo.pack(side=LEFT)
        self._header_logo.refresh()

        user = self.current_user or {}
        user_bar = ctk.CTkFrame(top_frame, fg_color="transparent")
        user_bar.grid(row=0, column=2, sticky=E)
        role = (user.get("role") or "staff").title()
        ctk.CTkButton(
            user_bar,
            text="Sign out",
            width=88,
            height=30,
            fg_color="transparent",
            border_width=1,
            text_color=("gray20", "gray85"),
            border_color=("gray65", "gray40"),
            hover_color=("gray88", "gray25"),
            command=self._show_login,
        ).pack(side=RIGHT)
        ctk.CTkButton(
            user_bar,
            text="My profile",
            width=96,
            height=30,
            fg_color="transparent",
            border_width=1,
            text_color=("gray20", "gray85"),
            border_color=("gray65", "gray40"),
            hover_color=("gray88", "gray25"),
            command=self._open_my_profile,
        ).pack(side=RIGHT, padx=(0, 8))
        self._header_user_label = ctk.CTkLabel(
            user_bar,
            text=f"{user.get('full_name', '')}  ·  {role}",
            font=ctk.CTkFont(size=13),
            text_color=CTK_HEADER_ACCENT_TEXT,
        )
        self._header_user_label.pack(side=RIGHT, padx=(0, 8))

        nav_frame = ctk.CTkFrame(self._content, fg_color="transparent")
        nav_frame.pack(fill=X, padx=12, pady=(0, 6))

        buttons = [
            ("Home", "home"),
            ("Products", "products"),
            ("Gallery", "gallery"),
            ("Sales", "sales"),
            ("Purchases", "purchases"),
            ("Reports", "reports"),
        ]

        for text, screen_name in buttons:
            btn = ctk.CTkButton(
                nav_frame,
                text=text,
                width=108,
                height=32,
                command=lambda s=screen_name: self.show_screen(s),
                **self._nav_bootstyle(screen_name, hover=False),
            )
            btn.pack(side=LEFT, padx=(0, 8))
            self._nav_buttons[screen_name] = btn
            btn.bind("<Enter>", lambda e, k=screen_name: self._on_nav_hover(k, True))
            btn.bind("<Leave>", lambda e, k=screen_name: self._on_nav_hover(k, False))

        foot = ctk.CTkFrame(self._content, fg_color="transparent")
        foot.pack(side=BOTTOM, fill=X, padx=12, pady=(0, 10))
        ttk.Separator(self._content, orient="horizontal").pack(side=BOTTOM, fill=X, padx=12, pady=(0, 0))
        ctk.CTkLabel(
            foot,
            text=format_app_footer_text(),
            font=ctk.CTkFont(size=11),
            text_color=CTK_TEXT_MUTED,
            anchor="w",
            wraplength=1100,
        ).pack(side=LEFT, padx=4, pady=(8, 6), fill=X, expand=True)

        scroll_wrap = ctk.CTkFrame(self._content, fg_color="transparent")
        scroll_wrap.pack(side=TOP, fill=BOTH, expand=True)
        scroll_wrap.columnconfigure(0, weight=1)
        scroll_wrap.rowconfigure(0, weight=1)

        _canvas_bg = TOKENS.BG_DARK if AppSettings().get_appearance() == "dark" else TOKENS.BG_LIGHT
        self._main_canvas = tk.Canvas(scroll_wrap, highlightthickness=0, bd=0, bg=_canvas_bg)
        self._main_vsb = ctk.CTkScrollbar(scroll_wrap, orientation="vertical", command=self._main_canvas.yview)
        self._main_canvas.configure(yscrollcommand=self._main_vsb.set)
        self._main_canvas.grid(row=0, column=0, sticky=NSEW)
        self._main_vsb.grid(row=0, column=1, sticky="ns")

        self._scrollable_inner = ctk.CTkFrame(self._main_canvas, fg_color="transparent")
        self._canvas_window = self._main_canvas.create_window((0, 0), window=self._scrollable_inner, anchor="nw")
        self._scrollable_inner.columnconfigure(0, weight=1)
        # No row weight: screen height follows content so scrollregion grows past the viewport.

        def _sync_scroll(_event=None):
            try:
                bbox = self._main_canvas.bbox("all")
                if bbox:
                    self._main_canvas.configure(scrollregion=bbox)
                    total_h = bbox[3] - bbox[1]
                else:
                    self._main_canvas.configure(scrollregion=(0, 0, 0, 0))
                    total_h = 0
                cw = self._main_canvas.winfo_width()
                if cw > 1 and self._canvas_window is not None:
                    self._main_canvas.itemconfigure(self._canvas_window, width=cw)
                ch = max(1, self._main_canvas.winfo_height())
                if self._main_vsb is not None:
                    if total_h > ch + 2:
                        self._main_vsb.grid(row=0, column=1, sticky="ns")
                    else:
                        self._main_vsb.grid_remove()
            except tk.TclError:
                pass

        def _on_canvas_configure(event):
            if self._canvas_window is not None:
                self._main_canvas.itemconfigure(self._canvas_window, width=event.width)
            _sync_scroll()

        self._scrollable_inner.bind("<Configure>", lambda e: _sync_scroll())
        self._main_canvas.bind("<Configure>", _on_canvas_configure)

        self._bind_main_scroll_wheel()

        self.screens = {}
        for screen_cls, key in _SCREEN_SPECS:
            screen = screen_cls(self._scrollable_inner, self)
            self.screens[key] = screen
            screen.grid(row=0, column=0, sticky="new")

        self.container = self._scrollable_inner

    def _unbind_main_scroll_wheel(self) -> None:
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            try:
                self.unbind_all(seq)
            except tk.TclError:
                pass

    def _main_scroll_mousewheel(self, event: tk.Event) -> None:
        if self._main_canvas is None or self._scrollable_inner is None:
            return
        w = event.widget
        inner = self._scrollable_inner
        under = False
        for _ in range(64):
            if w is None:
                break
            if w is inner:
                under = True
                break
            try:
                w = w.master
            except tk.TclError:
                break
        if not under:
            return
        try:
            wclass = str(event.widget.winfo_class())
        except tk.TclError:
            return
        if wclass in ("Treeview", "Listbox", "Text", "Spinbox", "TSpinbox"):
            return
        c = self._main_canvas
        if getattr(event, "delta", 0):
            c.yview_scroll(int(-1 * event.delta / 120), "units")
        elif getattr(event, "num", 0) == 4:
            c.yview_scroll(-1, "units")
        elif getattr(event, "num", 0) == 5:
            c.yview_scroll(1, "units")

    def _bind_main_scroll_wheel(self) -> None:
        self._unbind_main_scroll_wheel()
        self.bind_all("<MouseWheel>", self._main_scroll_mousewheel)
        self.bind_all("<Button-4>", self._main_scroll_mousewheel)
        self.bind_all("<Button-5>", self._main_scroll_mousewheel)

    def _nav_bootstyle(self, screen_name: str, *, hover: bool) -> dict:
        selected = screen_name == self._current_screen_name
        tx_on = ("#FFFFFF", "#FFFFFF")
        tx_muted = CTK_NAV_TEXT_MUTED
        border_muted = CTK_NAV_BORDER_MUTED
        border_pri = CTK_NAV_BORDER_ACCENT
        border_sales = CTK_NAV_BORDER_SALES
        fill_pri = CTK_NAV_SELECTED_FG
        fill_pri_h = CTK_NAV_SELECTED_HOVER
        fill_ok = CTK_NAV_SALES_SELECTED
        fill_ok_h = CTK_NAV_SALES_HOVER
        if screen_name == "sales" and selected:
            return {
                "fg_color": fill_ok,
                "hover_color": fill_ok_h,
                "border_width": 0,
                "text_color": tx_on,
            }
        if selected:
            return {
                "fg_color": fill_pri,
                "hover_color": fill_pri_h,
                "border_width": 0,
                "text_color": tx_on,
            }
        bc = border_pri if hover else border_muted
        if screen_name == "sales" and hover:
            bc = border_sales
        return {
            "fg_color": "transparent",
            "hover_color": CTK_NAV_HOVER_SURFACE,
            "border_width": 2,
            "border_color": bc,
            "text_color": tx_muted,
        }

    def _on_nav_hover(self, screen_name: str, entering: bool) -> None:
        btn = self._nav_buttons.get(screen_name)
        if btn is None:
            return
        try:
            btn.configure(**self._nav_bootstyle(screen_name, hover=entering))
        except tk.TclError:
            pass

    def _sync_nav_styles(self) -> None:
        for name, btn in self._nav_buttons.items():
            try:
                btn.configure(**self._nav_bootstyle(name, hover=False))
            except tk.TclError:
                pass

    def show_screen(self, screen_name):
        self._current_screen_name = screen_name
        self._sync_nav_styles()
        screen = self.screens[screen_name]
        screen.tkraise()
        if hasattr(screen, "refresh"):
            screen.refresh()
        if self._scrollable_inner is not None:
            self.after_idle(lambda: self._scrollable_inner.event_generate("<Configure>"))

    def add_product_to_sales_cart(self, product_id: int, quantity: float = 1.0) -> None:
        self.show_screen("sales")
        sale = self.screens.get("sales")
        if sale is not None and hasattr(sale, "add_to_cart_by_product_id"):
            sale.add_to_cart_by_product_id(int(product_id), float(quantity))

    def _pin_default_root_for_image_assets(self) -> None:
        """PIL ImageTk during ttkbootstrap ``theme_use`` may build PhotoImage without master."""
        tk._default_root = self

    def get_current_theme(self) -> str:
        return self.style.theme_use()

    def apply_theme(self, theme_name: str) -> bool:
        names = self.style.theme_names()
        if theme_name not in names:
            return False
        self._pin_default_root_for_image_assets()
        self.style.theme_use(theme_name)
        AppSettings().set_theme(theme_name)
        if theme_name == THEME_DARK:
            ctk.set_appearance_mode("Dark")
        elif theme_name == THEME_LIGHT:
            ctk.set_appearance_mode("Light")
        self._after_theme_change()
        return True

    def apply_appearance(self, appearance: str) -> bool:
        """Switch dark (superhero) / light (flatly) and persist `appearance` in app_settings."""
        if appearance not in ("dark", "light"):
            return False
        name = theme_for_appearance(appearance)
        names = self.style.theme_names()
        if name not in names:
            return False
        self._pin_default_root_for_image_assets()
        self.style.theme_use(name)
        AppSettings().set_appearance(appearance)
        ctk.set_appearance_mode("Dark" if appearance == "dark" else "Light")
        self._after_theme_change()
        return True

    def _after_theme_change(self) -> None:
        logo = getattr(self, "_header_logo", None)
        if logo is not None:
            try:
                logo.refresh()
            except Exception:
                pass
        canvas = getattr(self, "_main_canvas", None)
        if canvas is not None:
            try:
                _bg = TOKENS.BG_DARK if AppSettings().get_appearance() == "dark" else TOKENS.BG_LIGHT
                canvas.configure(bg=_bg)
            except tk.TclError:
                pass
        for scr in getattr(self, "screens", {}).values():
            fn = getattr(scr, "apply_theme_tokens", None)
            if callable(fn):
                try:
                    fn()
                except tk.TclError:
                    pass
        self.update_idletasks()

    def center_window(self):
        """Place window on screen; always sets WxH+X+Y (position-only strings confuse some WMs)."""
        self.update_idletasks()
        try:
            self.wm_state("normal")
        except tk.TclError:
            pass
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            w, h = WINDOW_WIDTH, WINDOW_HEIGHT
        w = min(w, max(400, sw - 24))
        h = min(h, max(300, sh - 24))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
