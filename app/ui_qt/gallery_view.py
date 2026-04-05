"""Product gallery — images and prices, best sellers first."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import PAD_MD
from app.services.product_service import ProductService
from app.ui.theme_tokens import TOKENS

from app.ui_qt.helpers_qt import format_money, warning_message
from app.ui_qt.products_view import ProductEditorDialogQt

_THUMB = 132


class _GalleryImageLabel(QLabel):
    clicked = Signal(int)

    def __init__(self, product_id: int, parent=None):
        super().__init__(parent)
        self._product_id = product_id
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._product_id)
        super().mousePressEvent(event)


class _GalleryPriceLabel(QLabel):
    add_to_cart = Signal(int)

    def __init__(self, product_id: int, text: str, parent=None):
        super().__init__(text, parent)
        self._product_id = product_id
        self.setCursor(Qt.PointingHandCursor)
        self.setAlignment(Qt.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.add_to_cart.emit(self._product_id)
        super().mousePressEvent(event)


class _GalleryNameLabel(QLabel):
    """Double-click opens full product editor (stock, expiry, QC)."""

    edit_requested = Signal(int)

    def __init__(self, product_id: int, text: str, parent=None):
        super().__init__(text, parent)
        self._product_id = product_id
        self.setCursor(Qt.PointingHandCursor)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.edit_requested.emit(self._product_id)
        super().mouseDoubleClickEvent(event)


class GalleryView(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._svc = ProductService()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(PAD_MD)

        title = QLabel("Gallery")
        title.setObjectName("title")
        root.addWidget(title)
        sub = QLabel(
            "Best sellers first. Use Add product or Inventory to grow the catalog. "
            "Click image to set photo · double-click name to edit (stock, expiry, QC) · "
            "click price to add to sale (qty 1).",
        )
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        root.addWidget(sub)

        act = QHBoxLayout()
        add_b = QPushButton("Add product")
        add_b.setObjectName("primary")
        add_b.setCursor(Qt.PointingHandCursor)
        add_b.clicked.connect(self._add_product)
        act.addWidget(add_b)
        inv_b = QPushButton("Products & inventory")
        inv_b.setCursor(Qt.PointingHandCursor)
        inv_b.clicked.connect(self._open_products)
        act.addWidget(inv_b)
        act.addStretch(1)
        root.addLayout(act)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Search"))
        self._search = QLineEdit()
        self._search.setFixedWidth(200)
        self._search.returnPressed.connect(self.refresh)
        bar.addWidget(self._search)
        bar.addWidget(QLabel("Category"))
        self._cat = QComboBox()
        self._cat.setMinimumWidth(180)
        bar.addWidget(self._cat)
        ap = QPushButton("Apply")
        ap.setObjectName("primary")
        ap.setCursor(Qt.PointingHandCursor)
        ap.clicked.connect(self.refresh)
        bar.addWidget(ap)
        bar.addStretch(1)
        root.addLayout(bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._inner = QWidget()
        self._grid = QGridLayout(self._inner)
        self._grid.setSpacing(12)
        scroll.setWidget(self._inner)
        root.addWidget(scroll, 1)

        self._cols = 4

    def _add_price_to_sales(self, product_id: int) -> None:
        if hasattr(self._main, "add_product_to_sales_cart"):
            self._main.add_product_to_sales_cart(product_id, 1.0)

    def _cross_refresh_products(self) -> None:
        pv = self._main._screens.get("products") if hasattr(self._main, "_screens") else None
        if pv is not None and hasattr(pv, "refresh"):
            try:
                pv.refresh()
            except Exception:
                pass

    def _add_product(self) -> None:
        cats = self._svc.list_categories()
        d = ProductEditorDialogQt(self.window(), self._svc, None, cats)
        d.exec()
        if d.saved:
            self._cross_refresh_products()
            self.refresh()

    def _open_products(self) -> None:
        if hasattr(self._main, "show_screen"):
            self._main.show_screen("products")

    def _edit_product(self, product_id: int) -> None:
        cats = self._svc.list_categories()
        d = ProductEditorDialogQt(self.window(), self._svc, product_id, cats)
        d.exec()
        if d.saved:
            self._cross_refresh_products()
            self.refresh()

    @staticmethod
    def _stock_row(product: dict) -> tuple[str, str]:
        """Return (caption, objectName or 'warn' for orange low-stock)."""
        qty = float(product.get("quantity_in_stock") or 0)
        min_l = float(product.get("minimum_stock_level") or 0)
        qtxt = str(int(qty)) if qty == int(qty) else f"{qty:.1f}"
        if qty <= 0:
            return f"Stock: {qtxt} · Out", "statusBad"
        if qty <= min_l:
            return f"Stock: {qtxt} · Low", "warn"
        return f"Stock: {qtxt}", "muted"

    def _pick_image_for_product(self, product_id: int) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.window(),
            "Product image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp);;All (*.*)",
        )
        if not path:
            return
        try:
            self._svc.set_product_image_from_file(product_id, path)
        except Exception as e:
            warning_message(self.window(), "Image", str(e))
            return
        self._cross_refresh_products()
        self.refresh()

    @staticmethod
    def _pixmap_thumb(path: str) -> QPixmap | None:
        p = Path(path)
        if not p.is_file():
            return None
        pm = QPixmap(str(p))
        if pm.isNull():
            return None
        return pm.scaled(_THUMB, _THUMB, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def apply_global_search(self, text: str) -> None:
        """Top-bar search: open gallery with name/SKU filter prefilled."""
        self._search.setText(text)
        self.refresh()

    def refresh(self) -> None:
        cats = ["(all)"] + self._svc.list_categories()
        self._cat.blockSignals(True)
        self._cat.clear()
        self._cat.addItems(cats)
        self._cat.blockSignals(False)

        search = self._search.text().strip() or None
        cat = self._cat.currentText()
        cat_arg = None if cat == "(all)" else cat

        try:
            rows = self._svc.list_active_products_by_units_sold(
                search=search,
                category=cat_arg,
                limit=240,
            )
        except Exception:
            rows = []

        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        if not rows:
            empty = QLabel("No products match your filters.")
            empty.setObjectName("muted")
            self._grid.addWidget(empty, 0, 0)
            return

        for col in range(self._cols):
            self._grid.setColumnStretch(col, 1)

        for idx, p in enumerate(rows):
            r, c = divmod(idx, self._cols)
            pid = int(p["id"])
            card = QFrame()
            card.setObjectName("card")
            cv = QVBoxLayout(card)
            cv.setAlignment(Qt.AlignHCenter)
            cv.setContentsMargins(12, 12, 12, 12)

            ipath = (p.get("image_path") or "").strip()
            pm = self._pixmap_thumb(ipath) if ipath else None
            img = _GalleryImageLabel(pid)
            img.setFixedSize(_THUMB, _THUMB)
            img.setAlignment(Qt.AlignCenter)
            img.clicked.connect(self._pick_image_for_product)
            if pm is not None:
                img.setPixmap(pm)
            else:
                img.setText("No image\n(click)")
                img.setObjectName("muted")
            cv.addWidget(img, alignment=Qt.AlignCenter)

            nm = _GalleryNameLabel(pid, (p.get("name") or "—")[:40])
            nm.edit_requested.connect(self._edit_product)
            cv.addWidget(nm)

            st_txt, st_kind = self._stock_row(p)
            st = QLabel(st_txt)
            st.setAlignment(Qt.AlignCenter)
            if st_kind == "statusBad":
                st.setObjectName("statusBad")
            elif st_kind == "warn":
                st.setStyleSheet(f"color: {TOKENS.WARNING}; font-size: 11px;")
            else:
                st.setObjectName("muted")
            cv.addWidget(st)

            pr = _GalleryPriceLabel(pid, format_money(float(p.get("selling_price") or 0)))
            pr.setObjectName("kpiValueSm")
            pr.add_to_cart.connect(self._add_price_to_sales)
            cv.addWidget(pr)

            us = float(p.get("units_sold") or 0)
            us_txt = f"{int(us)} sold" if us == int(us) else f"{us:.1f} sold"
            sold = QLabel(us_txt)
            sold.setObjectName("muted")
            sold.setAlignment(Qt.AlignCenter)
            cv.addWidget(sold)

            card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            self._grid.addWidget(card, r, c, Qt.AlignTop)
