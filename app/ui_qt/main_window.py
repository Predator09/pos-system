"""Qt main window: login stack, shell with sidebar + top bar + stacked content (dashboard-style)."""

from datetime import date

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app.config import WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH, format_app_footer_text
from app.services.shop_settings import get_display_shop_name
from app.services.app_settings import AppSettings, theme_for_appearance
from app.services.backup_service import BackupService

from app.ui_qt.gallery_view import GalleryView
from app.ui_qt.home_view import HomeView
from app.ui_qt.login_view import LoginView
from app.ui_qt.logo_widget import ShopLogoLabel
from app.ui_qt.products_view import ProductsView
from app.ui_qt.purchases_view import PurchasesView
from app.ui_qt.reports_view import ReportsView
from app.ui_qt.sales_view import SalesView
from app.ui_qt.motion_qt import fade_in_widget
from app.ui_qt.profile_dialog_qt import ProfileDialogQt
from app.ui_qt.styles import get_qt_stylesheet
from app.ui_qt.helpers_qt import info_message
from app.services.product_service import ProductService

# (display label, screen key, show chevron like reference nav)
_NAV: tuple[tuple[str, str, bool], ...] = (
    ("Dashboard", "home", False),
    ("Products", "products", True),
    ("Gallery", "gallery", True),
    ("Point of Sale", "sales", True),
    ("Purchases", "purchases", True),
    ("Reports", "reports", True),
)

_TOP_BAR_META: dict[str, tuple[str, str]] = {
    "home": ("Dashboard Overview", ""),
    "products": ("Products & inventory", "Catalog, pricing, and stock"),
    "gallery": ("Gallery", "Best sellers first · images & prices"),
    "sales": ("Point of Sale", "__shop_register__"),
    "purchases": ("Purchases", "Purchase stock · inventory & costing"),
    "reports": ("Reports", "Sales, inventory & CSV exports"),
}


def _nav_icon(style: QStyle, key: str) -> QIcon:
    m = {
        "home": QStyle.StandardPixmap.SP_DirHomeIcon,
        "products": QStyle.StandardPixmap.SP_FileDialogDetailedView,
        "gallery": QStyle.StandardPixmap.SP_FileDialogListView,
        "sales": QStyle.StandardPixmap.SP_ComputerIcon,
        "purchases": QStyle.StandardPixmap.SP_DialogOpenButton,
        "reports": QStyle.StandardPixmap.SP_FileDialogInfoView,
    }
    return style.standardIcon(m.get(key, QStyle.StandardPixmap.SP_FileIcon))


class MainQtWindow(QMainWindow):
    """Qt shell: left sidebar (brand + icons), top bar (title + search + user), stacked views."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(960, 540)

        self.current_user: dict | None = None
        self._screens: dict[str, QWidget] = {}
        self._name_to_row: dict[str, int] = {}
        self._shell: QWidget | None = None
        self._nav_list: QListWidget | None = None
        self._page_title: QLabel | None = None
        self._page_subtitle: QLabel | None = None
        self._sidebar_logo: ShopLogoLabel | None = None
        self._user_label: QLabel | None = None
        self._avatar: QLabel | None = None
        self._brand_name_label: QLabel | None = None
        self._footer_text_label: QLabel | None = None

        self._root_stack = QStackedWidget()
        self.setCentralWidget(self._root_stack)

        self._login_page = LoginView(self)
        self._root_stack.addWidget(self._login_page)

        self._top_bar_timer = QTimer(self)
        self._top_bar_timer.timeout.connect(self._refresh_top_bar_clock)
        self._top_bar_timer.start(30000)

    def _refresh_top_bar_clock(self) -> None:
        if self._shell is None or self._page_subtitle is None or self._nav_list is None:
            return
        row = self._nav_list.currentRow()
        if row < 0:
            return
        key = _NAV[row][1]
        if key == "home":
            self._page_subtitle.setText(date.today().strftime("%d %B, %Y"))

    def _refresh_footer_text(self) -> None:
        if self._footer_text_label is not None:
            self._footer_text_label.setText(format_app_footer_text())

    def enter_app(self, user: dict) -> None:
        self.current_user = user
        backup = BackupService()
        backup.auto_backup_daily()
        if self._shell is None:
            self._build_shell()
            self._root_stack.addWidget(self._shell)
        self._sync_user_widgets()
        if self._sidebar_logo is not None:
            self._sidebar_logo.refresh()
        if self._brand_name_label is not None:
            self._brand_name_label.setText(get_display_shop_name())
        self._refresh_footer_text()
        self.show_screen("home")
        self._root_stack.setCurrentWidget(self._shell)
        fade_in_widget(self._shell, 300)

    def _user_bar_text(self) -> str:
        u = self.current_user or {}
        role = (u.get("role") or "staff").title()
        name = (u.get("full_name") or u.get("username") or "User").strip()
        return f"{name}  ·  {role}"

    def _sync_user_widgets(self) -> None:
        if self._user_label is not None:
            self._user_label.setText(self._user_bar_text())
        if self._avatar is not None:
            u = self.current_user or {}
            raw = (u.get("full_name") or u.get("username") or "?").strip()
            ch = raw[0].upper() if raw else "?"
            self._avatar.setText(ch)

    def _update_top_bar(self, screen_key: str) -> None:
        if self._page_title is None or self._page_subtitle is None:
            return
        title, sub = _TOP_BAR_META.get(screen_key, ("", ""))
        self._page_title.setText(title)
        if screen_key == "home":
            self._page_subtitle.setText(date.today().strftime("%d %B, %Y"))
        elif screen_key == "sales":
            self._page_subtitle.setText(f"{get_display_shop_name()} · Register")
        else:
            self._page_subtitle.setText(sub)
        gs = getattr(self, "_global_search", None)
        if gs is not None:
            gs.setVisible(screen_key != "sales")

    def _build_shell(self) -> None:
        shell = QWidget()
        shell.setObjectName("shellRoot")
        outer = QHBoxLayout(shell)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(16)

        # ---- Sidebar (full height) ----
        side = QFrame()
        side.setObjectName("sidebarRail")
        side.setFixedWidth(268)
        side_l = QVBoxLayout(side)
        side_l.setContentsMargins(14, 18, 14, 18)
        side_l.setSpacing(12)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)
        self._sidebar_logo = ShopLogoLabel(side, size=48, editable=True)
        brand_row.addWidget(self._sidebar_logo, alignment=Qt.AlignTop)
        brand_txt = QVBoxLayout()
        brand_txt.setSpacing(2)
        self._brand_name_label = QLabel(get_display_shop_name())
        self._brand_name_label.setObjectName("sidebarBrandName")
        brand_txt.addWidget(self._brand_name_label)
        bt = QLabel("POS · Inventory")
        bt.setObjectName("sidebarBrandTag")
        brand_txt.addWidget(bt)
        brand_row.addLayout(brand_txt, 1)
        side_l.addLayout(brand_row)

        side_l.addSpacing(8)

        self._nav_list = QListWidget()
        self._nav_list.setObjectName("sidebarNav")
        self._nav_list.setIconSize(QSize(22, 22))
        self._nav_list.setSpacing(4)
        self._nav_list.setFocusPolicy(Qt.StrongFocus)
        sty = QApplication.instance().style() if QApplication.instance() else None
        for i, (label, key, chev) in enumerate(_NAV):
            text = f"{label}  ›" if chev else label
            item = QListWidgetItem(_nav_icon(sty, key) if sty else QIcon(), f"  {text}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._nav_list.addItem(item)
            self._name_to_row[key] = i
        self._nav_list.currentRowChanged.connect(self._on_nav_row)
        side_l.addWidget(self._nav_list, 1)

        outer.addWidget(side)

        # ---- Right: top bar + content ----
        right = QWidget()
        right.setObjectName("contentHost")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        top = QFrame()
        top.setObjectName("topBar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(22, 16, 22, 16)
        top_layout.setSpacing(16)

        titles = QVBoxLayout()
        titles.setSpacing(4)
        self._page_title = QLabel("Dashboard Overview")
        self._page_title.setObjectName("pageTitle")
        titles.addWidget(self._page_title)
        self._page_subtitle = QLabel("")
        self._page_subtitle.setObjectName("pageSubtitle")
        titles.addWidget(self._page_subtitle)
        top_layout.addLayout(titles)

        top_layout.addStretch(1)

        self._global_search = QLineEdit()
        self._global_search.setObjectName("globalSearch")
        self._global_search.setPlaceholderText("Search products, SKU, invoices…")
        self._global_search.setClearButtonEnabled(True)
        self._global_search.setMinimumWidth(280)
        self._global_search.setMaximumWidth(400)
        top_layout.addWidget(self._global_search)
        self._global_search.returnPressed.connect(self._on_global_search_submit)

        bell = QPushButton("🔔")
        bell.setObjectName("iconButton")
        bell.setCursor(Qt.PointingHandCursor)
        bell.setFixedSize(42, 42)
        bell.setToolTip("Low-stock summary (at or below each SKU minimum)")
        bell.clicked.connect(self._on_bell_alerts)
        top_layout.addWidget(bell)

        self._avatar = QLabel("?")
        self._avatar.setObjectName("userAvatar")
        self._avatar.setAlignment(Qt.AlignCenter)
        self._avatar.setFixedSize(42, 42)
        top_layout.addWidget(self._avatar)

        self._user_label = QLabel(self._user_bar_text())
        self._user_label.setObjectName("topBarUser")
        top_layout.addWidget(self._user_label)

        prof = QPushButton("My profile")
        prof.setObjectName("ghost")
        prof.setCursor(Qt.PointingHandCursor)
        prof.clicked.connect(self._open_my_profile)
        top_layout.addWidget(prof)

        so = QPushButton("Sign out")
        so.setObjectName("ghost")
        so.setCursor(Qt.PointingHandCursor)
        so.clicked.connect(self.show_login)
        top_layout.addWidget(so)

        rv.addWidget(top)

        self._content_stack = QStackedWidget()
        self._screens["home"] = HomeView(self)
        self._screens["products"] = ProductsView(self)
        self._screens["gallery"] = GalleryView(self)
        self._screens["sales"] = SalesView(self)
        self._screens["purchases"] = PurchasesView(self)
        self._screens["reports"] = ReportsView(self)
        for _a, key, _b in _NAV:
            self._content_stack.addWidget(self._screens[key])

        self._content_scroll = QScrollArea()
        self._content_scroll.setObjectName("mainContentScroll")
        self._content_scroll.setWidgetResizable(True)
        self._content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content_scroll.setWidget(self._content_stack)
        rv.addWidget(self._content_scroll, 1)

        footer = QFrame()
        footer.setObjectName("appFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(22, 10, 22, 12)
        self._footer_text_label = QLabel(format_app_footer_text())
        self._footer_text_label.setObjectName("appFooterText")
        self._footer_text_label.setWordWrap(True)
        fl.addWidget(self._footer_text_label, 1)
        rv.addWidget(footer, 0)

        outer.addWidget(right, 1)

        self._shell = shell
        self._update_top_bar("home")

    def _on_nav_row(self, row: int) -> None:
        if row < 0:
            return
        key = _NAV[row][1]
        self._content_stack.setCurrentIndex(row)
        self._scroll_content_to_top()
        self._update_top_bar(key)
        screen = self._screens.get(key)
        if screen is not None and hasattr(screen, "refresh"):
            screen.refresh()

    def _scroll_content_to_top(self) -> None:
        sc = getattr(self, "_content_scroll", None)
        if sc is not None:
            sc.verticalScrollBar().setValue(0)

    def show_screen(self, screen_name: str) -> None:
        row = self._name_to_row.get(screen_name, 0)
        if self._nav_list is not None:
            self._nav_list.blockSignals(True)
            self._nav_list.setCurrentRow(row)
            self._nav_list.blockSignals(False)
        self._content_stack.setCurrentIndex(row)
        self._scroll_content_to_top()
        self._update_top_bar(screen_name)
        screen = self._screens.get(screen_name)
        if screen is not None and hasattr(screen, "refresh"):
            screen.refresh()

    def add_product_to_sales_cart(self, product_id: int, quantity: float = 1.0) -> None:
        self.show_screen("sales")
        sale = self._screens.get("sales")
        if sale is not None and hasattr(sale, "add_to_cart_by_product_id"):
            sale.add_to_cart_by_product_id(int(product_id), float(quantity))

    def _open_my_profile(self) -> None:
        ProfileDialogQt(self, self).exec()

    def _on_global_search_submit(self) -> None:
        if self._shell is None or self._global_search is None:
            return
        q = self._global_search.text().strip()
        if not q:
            return
        q_up = q.upper()
        if q_up.startswith("INV"):
            rv = self._screens.get("reports")
            if rv is not None and rv.show_invoice_from_global_search(q):
                self.show_screen("reports")
                self._global_search.clear()
                return
        ps = ProductService()
        row = ps.get_product_by_code(q) or ps.get_product_by_barcode(q)
        if row and row.get("is_active"):
            self.add_product_to_sales_cart(int(row["id"]), 1.0)
            self._global_search.clear()
            return
        hits = ps.search_products(q)
        if len(hits) == 1:
            self.add_product_to_sales_cart(int(hits[0]["id"]), 1.0)
            self._global_search.clear()
            return
        pv = self._screens.get("products")
        if pv is not None:
            self.show_screen("products")
            pv.apply_global_filter(q)

    def _on_bell_alerts(self) -> None:
        low = ProductService().get_low_stock()
        n = len(low)
        if n == 0:
            info_message(self, "Stock alerts", "No items are at or below their minimum stock level.")
            return
        lines = []
        for p in low[:10]:
            code = (p.get("code") or "").strip()
            raw_name = p.get("name") or "—"
            name = raw_name if len(raw_name) <= 43 else raw_name[:42] + "…"
            lines.append(f"• {code} — {name}")
        body = "\n".join(lines)
        if n > 10:
            body += f"\n… and {n - 10} more"
        info_message(self, f"Low stock ({n})", body)

    def show_login(self) -> None:
        self.current_user = None
        setattr(self._login_page, "_did_entrance_fade", False)
        self._root_stack.setCurrentWidget(self._login_page)

    def get_current_theme(self) -> str:
        th = AppSettings().get_theme()
        return th if th else AppSettings().get_appearance()

    def apply_appearance(self, appearance: str) -> bool:
        if appearance not in ("dark", "light"):
            return False
        theme_for_appearance(appearance)
        AppSettings().set_appearance(appearance)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(get_qt_stylesheet(appearance))
        pv = self._screens.get("products")
        if pv is not None:
            fn = getattr(pv, "apply_theme_tokens", None)
            if callable(fn):
                fn()
        return True
