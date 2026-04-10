"""Products & inventory Qt view; same ProductService usage as Tk ProductsScreen."""

from __future__ import annotations

import csv

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import PAD_MD
from app.ui.date_display import format_iso_date_as_display, parse_expiry_input
from app.services.app_settings import AppSettings
from app.services.product_service import ProductService
from app.ui.theme_tokens import product_active_row_surface

from app.ui_qt.helpers_qt import ask_yes_no, format_money, info_message, warning_message

_TREE_COLS = ("id", "name", "pc", "barcode", "category", "price", "stock", "cost", "status", "expiry")
_TABLE_HEADERS = (
    "ID",
    "Name",
    "PC",
    "Barcode",
    "Category",
    "Price",
    "Stock",
    "Cost",
    "Status",
    "Expiry",
)
_CSV_FIELDS = [
    "id",
    "code",
    "barcode",
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


class ProductEditorDialogQt(QDialog):
    def __init__(self, parent, service: ProductService, product_id: int | None, categories: list[str]):
        super().__init__(parent)
        self.service = service
        self.product_id = product_id
        self.saved = False
        self.setWindowTitle("Product" if product_id else "New product")
        self.resize(520, 600)

        outer = QVBoxLayout(self)
        f = QFormLayout()
        self._name = QLineEdit()
        self._category = QComboBox()
        self._category.setEditable(True)
        self._category.addItems([""] + categories)
        self._code = QLineEdit()
        self._barcode = QLineEdit()
        self._price = QLineEdit("0")
        self._cost = QLineEdit("0")
        self._stock = QLineEdit("0")
        self._min_alert = QLineEdit("10")
        self._status = QComboBox()
        self._status.addItems(["active", "inactive"])
        self._expiry = QLineEdit()
        self._expiry.setPlaceholderText("DD-MM-YYYY")
        self._image = QLineEdit()
        img_browse = QPushButton("Browse…")
        img_browse.clicked.connect(self._browse_image)
        img_row = QWidget()
        ir = QHBoxLayout(img_row)
        ir.setContentsMargins(0, 0, 0, 0)
        ir.addWidget(self._image, 1)
        ir.addWidget(img_browse)
        self._desc = QLineEdit()

        f.addRow("Name", self._name)
        f.addRow("Category", self._category)
        f.addRow("PC", self._code)
        f.addRow("Barcode (optional)", self._barcode)
        f.addRow("Selling price (GMD)", self._price)
        f.addRow("Cost (GMD)", self._cost)
        f.addRow("Stock qty", self._stock)
        f.addRow("Min alert level", self._min_alert)
        f.addRow("Status", self._status)
        f.addRow("Expiry (DD-MM-YYYY)", self._expiry)
        f.addRow("Image path", img_row)
        f.addRow("Description", self._desc)

        if product_id:
            p = service.get_product(product_id)
            if p:
                self._name.setText(p.get("name") or "")
                cat = p.get("category") or ""
                ix = self._category.findText(cat)
                if ix >= 0:
                    self._category.setCurrentIndex(ix)
                else:
                    self._category.setCurrentText(cat)
                self._code.setText(p.get("code") or "")
                self._barcode.setText((p.get("barcode") or "") or "")
                self._price.setText(str(p.get("selling_price") or 0))
                self._cost.setText(str(p.get("cost_price") or 0))
                self._stock.setText(str(p.get("quantity_in_stock") or 0))
                self._min_alert.setText(str(p.get("minimum_stock_level") or 10))
                self._status.setCurrentIndex(0 if p.get("is_active") else 1)
                ex0 = (p.get("expiry_date") or "") or ""
                self._expiry.setText(format_iso_date_as_display(ex0) if ex0 else "")
                self._image.setText((p.get("image_path") or "") or "")
                self._desc.setText(p.get("description") or "")
            outer.addWidget(
                QLabel("PC is your internal product code. Barcode is for scanning (unique when set).")
            )

        outer.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        save_btn = bb.button(QDialogButtonBox.StandardButton.Save)
        if save_btn is not None:
            save_btn.setObjectName("primary")
        outer.addWidget(bb)

    def _browse_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Product image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp);;All (*.*)",
        )
        if path:
            self._image.setText(path)

    @staticmethod
    def _parse_float(s: str, label: str) -> float:
        try:
            return float(str(s).strip().replace(",", ""))
        except ValueError as e:
            raise ValueError(f"{label}: invalid number") from e

    def _save(self) -> None:
        name = self._name.text().strip()
        code = self._code.text().strip()
        bc_raw = self._barcode.text().strip()
        bc = bc_raw if bc_raw else None
        if not name or not code:
            warning_message(self, "Product", "Name and product code (PC) are required.")
            return
        if bc:
            holder = self.service.get_product_by_barcode(bc)
            if holder and (not self.product_id or int(holder["id"]) != int(self.product_id)):
                warning_message(self, "Product", "That barcode is already used on another product.")
                return
        try:
            price = self._parse_float(self._price.text(), "Price")
            cost = self._parse_float(self._cost.text(), "Cost")
            stock = self._parse_float(self._stock.text(), "Stock")
            min_a = self._parse_float(self._min_alert.text(), "Min alert")
        except ValueError as e:
            warning_message(self, "Product", str(e))
            return
        exp_raw = self._expiry.text().strip()
        try:
            exp = parse_expiry_input(exp_raw)
        except ValueError:
            warning_message(self, "Product", "Use expiry format DD-MM-YYYY or leave blank.")
            return
        is_active = 1 if self._status.currentText() == "active" else 0
        img = self._image.text().strip() or None
        desc = self._desc.text().strip() or None
        cat = self._category.currentText().strip() or None
        try:
            if self.product_id:
                self.service.update_product(
                    self.product_id,
                    name=name,
                    code=code,
                    barcode=bc,
                    category=cat,
                    description=desc,
                    cost_price=cost,
                    selling_price=price,
                    quantity_in_stock=stock,
                    minimum_stock_level=min_a,
                    is_active=is_active,
                    expiry_date=exp,
                    image_path=img,
                )
            else:
                if self.service.get_product_by_code(code):
                    warning_message(self, "Product", "That product code (PC) already exists.")
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
                    expiry_date=exp,
                    image_path=img,
                    barcode=bc,
                )
        except Exception as e:
            warning_message(self, "Product", f"Save failed: {e}")
            return
        self.saved = True
        self.accept()


class ProductsView(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._svc = ProductService()
        self._all_products: list[dict] = []
        self._stat_labels: dict[str, QLabel] = {}
        self._filter_timer: QTimer | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        main_card = QFrame()
        main_card.setObjectName("card")
        card_inner = QVBoxLayout(main_card)
        card_inner.setContentsMargins(16, 16, 16, 16)
        card_inner.setSpacing(PAD_MD)

        head = QHBoxLayout()
        ph = QLabel("Del deactivate · selection for bulk")
        ph.setObjectName("muted")
        head.addWidget(ph, 1)
        hb = QHBoxLayout()
        hb.setSpacing(10)
        np = QPushButton("New product", clicked=self._new_product)
        np.setObjectName("primary")
        np.setCursor(Qt.PointingHandCursor)
        hb.addWidget(np)
        im = QPushButton("Import CSV", clicked=self._import_csv)
        im.setCursor(Qt.PointingHandCursor)
        hb.addWidget(im)
        ex = QPushButton("Export CSV", clicked=self._export_csv)
        ex.setCursor(Qt.PointingHandCursor)
        hb.addWidget(ex)
        head.addLayout(hb)
        card_inner.addLayout(head)

        stats = QHBoxLayout()
        stats.setSpacing(16)
        for key, title in (
            ("total", "Total"),
            ("low", "Low stock"),
            ("out", "Out of stock"),
            ("value", "Inv. value"),
            ("topcat", "Top category"),
            ("avg", "Avg price"),
        ):
            bx = QVBoxLayout()
            st = QLabel(title)
            st.setObjectName("muted")
            bx.addWidget(st)
            lab = QLabel("—")
            lab.setObjectName("kpiValueSm")
            bx.addWidget(lab)
            stats.addLayout(bx)
            self._stat_labels[key] = lab
        card_inner.addLayout(stats)

        filt = QGridLayout()
        self._search = QLineEdit()
        self._search.textChanged.connect(self._schedule_filter)
        self._cat = QComboBox()
        self._cat.setEditable(False)
        self._cat.currentTextChanged.connect(lambda _t: self._apply_filters())
        self._pmin = QLineEdit()
        self._pmax = QLineEdit()
        self._stock = QComboBox()
        self._stock.addItems(["(all)", "low", "out", "ok"])
        self._stock.currentTextChanged.connect(lambda _t: self._apply_filters())
        self._status = QComboBox()
        self._status.addItems(["(all)", "active", "inactive", "expired"])
        self._status.currentTextChanged.connect(lambda _t: self._apply_filters())

        r = 0
        filt.addWidget(QLabel("Name"), r, 0)
        filt.addWidget(QLabel("Category"), r, 1)
        filt.addWidget(QLabel("Price min"), r, 2)
        filt.addWidget(QLabel("Price max"), r, 3)
        filt.addWidget(QLabel("Stock"), r, 4)
        filt.addWidget(QLabel("Status"), r, 5)
        r += 1
        filt.addWidget(self._search, r, 0)
        filt.addWidget(self._cat, r, 1)
        filt.addWidget(self._pmin, r, 2)
        filt.addWidget(self._pmax, r, 3)
        filt.addWidget(self._stock, r, 4)
        filt.addWidget(self._status, r, 5)
        r += 1
        fa = QHBoxLayout()
        fa.addWidget(QPushButton("Apply", clicked=self._apply_filters))
        fa.addWidget(QPushButton("Clear", clicked=self._clear_filters))
        filt.addLayout(fa, r, 0, 1, 6)
        card_inner.addLayout(filt)

        self._bulk_frame = QWidget()
        bl = QHBoxLayout(self._bulk_frame)
        bl.addWidget(QLabel("Selection:"))
        self._sel_count = QLabel("0")
        bl.addWidget(self._sel_count)
        bl.addWidget(QPushButton("Restock +5", clicked=lambda: self._bulk_restock(5)))
        bl.addWidget(QPushButton("Deactivate", clicked=self._bulk_deactivate))
        bl.addWidget(QPushButton("Price +/- %", clicked=self._bulk_price_pct))
        bl.addWidget(QPushButton("Set min alert", clicked=self._bulk_min_alert))
        bl.addStretch(1)
        self._bulk_frame.setVisible(False)
        card_inner.addWidget(self._bulk_frame)

        self._table = QTableWidget(0, len(_TREE_COLS))
        self._table.setHorizontalHeaderLabels(list(_TABLE_HEADERS))
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.itemSelectionChanged.connect(self._on_select)
        self._table.cellDoubleClicked.connect(lambda *_: self._edit_selected())
        card_inner.addWidget(self._table, 1)

        keys = QHBoxLayout()
        keys.addWidget(QLabel("Keys: Del=deactivate"))
        card_inner.addLayout(keys)

        root.addWidget(main_card, 1)

        self._table.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self._table and event.type() == QEvent.KeyPress and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key_Insert:
                self._new_product()
                return True
            if event.key() == Qt.Key_F2:
                self._edit_selected()
                return True
            if event.key() == Qt.Key_Delete:
                self._delete_selected()
                return True
        return super().eventFilter(watched, event)

    def _schedule_filter(self) -> None:
        if self._filter_timer is None:
            self._filter_timer = QTimer(self)
            self._filter_timer.setSingleShot(True)
            self._filter_timer.timeout.connect(self._apply_filters)
        self._filter_timer.stop()
        self._filter_timer.start(180)

    def _parse_opt_float(self, s: str) -> float | None:
        t = str(s).strip().replace(",", "")
        if not t:
            return None
        try:
            return float(t)
        except ValueError:
            return None

    def _passes_filters(self, p: dict) -> bool:
        q = self._search.text().strip().lower()
        bc = (p.get("barcode") or "").lower()
        if q and q not in (p.get("name") or "").lower() and q not in (p.get("code") or "").lower() and q not in bc:
            return False
        cat = self._cat.currentText()
        if cat and cat != "(all)":
            if (p.get("category") or "") != cat:
                return False
        pmin = self._parse_opt_float(self._pmin.text())
        pmax = self._parse_opt_float(self._pmax.text())
        price = float(p.get("selling_price") or 0)
        if pmin is not None and price < pmin:
            return False
        if pmax is not None and price > pmax:
            return False
        st = ProductService.row_status(p)
        fs = self._status.currentText()
        if fs and fs != "(all)" and st != fs:
            return False
        sk = self._stock.currentText()
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

    def _apply_filters(self) -> None:
        self._table.setRowCount(0)
        for p in self._all_products:
            if not self._passes_filters(p):
                continue
            pid = int(p["id"])
            qty = float(p.get("quantity_in_stock") or 0)
            price = float(p.get("selling_price") or 0)
            ex0 = (p.get("expiry_date") or "").strip()
            exp = format_iso_date_as_display(ex0) if ex0 else "—"
            row = self._table.rowCount()
            self._table.insertRow(row)
            vals = (
                str(pid),
                p.get("name") or "",
                p.get("code") or "—",
                (p.get("barcode") or "") or "—",
                p.get("category") or "—",
                format_money(price),
                f"{qty:g}" if qty == int(qty) else f"{qty:.2f}",
                format_money(float(p.get("cost_price") or 0)),
                ProductService.inventory_status_display(p),
                exp,
            )
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self._table.setItem(row, c, it)
            self._table.item(row, 0).setData(Qt.UserRole, pid)
            self._apply_product_row_status_style(row, p)
        self._on_select()

    def _apply_product_row_status_style(self, row: int, p: dict) -> None:
        appearance = AppSettings().get_appearance()
        is_dark = (appearance or "").lower() == "dark"
        bg_s, fg_s = product_active_row_surface(appearance)
        row_bg, base_fg = QColor(bg_s), QColor(fg_s)
        red_fg = QColor("#f87171") if is_dark else QColor("#b91c1c")
        yellow_fg = QColor("#fbbf24") if is_dark else QColor("#b45309")

        font = QFont()
        font.setPointSize(10)
        status_col = _TREE_COLS.index("status")
        for c in range(self._table.columnCount()):
            it = self._table.item(row, c)
            if it is None:
                continue
            it.setBackground(row_bg)
            it.setForeground(base_fg)
            it.setFont(font)

        tag = ProductService.inventory_row_tag(p)
        it_status = self._table.item(row, status_col)
        if it_status is None:
            return
        if tag in ("expired", "bad"):
            it_status.setForeground(red_fg)
        elif tag in ("low", "inactive"):
            it_status.setForeground(yellow_fg)

    def apply_theme_tokens(self) -> None:
        """Re-tint inventory rows when light/dark stylesheet changes."""
        for row in range(self._table.rowCount()):
            it0 = self._table.item(row, 0)
            if it0 is None:
                continue
            pid = it0.data(Qt.UserRole)
            if pid is None:
                continue
            try:
                pid_i = int(pid)
            except (TypeError, ValueError):
                continue
            p = next((x for x in self._all_products if int(x.get("id", 0)) == pid_i), None)
            if p is not None:
                self._apply_product_row_status_style(row, p)

    def _clear_filters(self) -> None:
        self._search.clear()
        self._cat.setCurrentText("(all)")
        self._status.setCurrentText("(all)")
        self._stock.setCurrentText("(all)")
        self._pmin.clear()
        self._pmax.clear()
        self._apply_filters()

    def _selected_ids(self) -> list[int]:
        out: list[int] = []
        for it in self._table.selectedItems():
            if it.column() != 0:
                continue
            pid = it.data(Qt.UserRole)
            if pid is not None:
                try:
                    out.append(int(pid))
                except (TypeError, ValueError):
                    pass
        return sorted(set(out))

    def _on_select(self) -> None:
        n = len(self._selected_ids())
        self._sel_count.setText(str(n))
        self._bulk_frame.setVisible(n > 0)

    def _update_stats(self) -> None:
        s = self._svc.get_inventory_dashboard_stats()
        self._stat_labels["total"].setText(str(s["total_products"]))
        self._stat_labels["low"].setText(str(s["low_stock"]))
        self._stat_labels["out"].setText(str(s["out_of_stock"]))
        self._stat_labels["value"].setText(format_money(s["inventory_value"]))
        self._stat_labels["topcat"].setText(s["top_category"] or "—")
        self._stat_labels["avg"].setText(format_money(s["avg_price"]))

    def _refresh_category_combo(self) -> None:
        prev = self._cat.currentText() if self._cat.count() else "(all)"
        cats = ["(all)"] + self._svc.list_categories()
        self._cat.blockSignals(True)
        self._cat.clear()
        self._cat.addItems(cats)
        if prev not in cats:
            self._cat.setCurrentIndex(0)
        else:
            self._cat.setCurrentText(prev)
        self._cat.blockSignals(False)

    def apply_global_filter(self, text: str) -> None:
        """Top-bar global search: jump here with the catalog filter prefilled."""
        self._search.setText(text)
        self._apply_filters()

    def refresh(self) -> None:
        self._all_products = self._svc.list_all_products()
        self._refresh_category_combo()
        self._update_stats()
        self._apply_filters()

    def _new_product(self) -> None:
        cats = self._svc.list_categories()
        d = ProductEditorDialogQt(self.window(), self._svc, None, cats)
        if d.exec() == QDialog.DialogCode.Accepted and d.saved:
            self.refresh()

    def _edit_selected(self) -> None:
        ids = self._selected_ids()
        if len(ids) != 1:
            warning_message(self.window(), "Products", "Select one product to edit.")
            return
        cats = self._svc.list_categories()
        d = ProductEditorDialogQt(self.window(), self._svc, ids[0], cats)
        if d.exec() == QDialog.DialogCode.Accepted and d.saved:
            self.refresh()

    def _delete_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            warning_message(self.window(), "Products", "Select at least one product.")
            return
        if not ask_yes_no(self.window(), "Deactivate", f"Mark {len(ids)} product(s) as inactive?"):
            return
        self._svc.bulk_deactivate(ids)
        self.refresh()

    def _bulk_restock(self, n: float) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        self._svc.bulk_add_stock(ids, n)
        self.refresh()

    def _bulk_deactivate(self) -> None:
        self._delete_selected()

    def _bulk_price_pct(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        v, ok = QInputDialog.getDouble(
            self.window(),
            "Price adjustment",
            "Percent change (e.g. 10 for +10%, -5 for -5%):",
            0.0,
            -100.0,
            100.0,
            2,
        )
        if not ok:
            return
        self._svc.bulk_adjust_selling_price_percent(ids, v)
        self.refresh()

    def _bulk_min_alert(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        v, ok = QInputDialog.getDouble(
            self.window(),
            "Minimum stock alert",
            "New minimum level for all selected:",
            10.0,
            0.0,
            1_000_000.0,
            2,
        )
        if not ok:
            return
        self._svc.bulk_set_minimum_stock(ids, v)
        self.refresh()

    def _export_csv(self) -> None:
        rows = [p for p in self._all_products if self._passes_filters(p)]
        if not rows:
            warning_message(self.window(), "Export", "No rows to export (adjust filters).")
            return
        path, _ = QFileDialog.getSaveFileName(
            self.window(),
            "Export products",
            "",
            "CSV (*.csv)",
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
                            "barcode": p.get("barcode") or "",
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
            warning_message(self.window(), "Export", f"Export failed: {e}")
            return
        info_message(self.window(), "Export", f"Exported {len(rows)} row(s).")

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.window(),
            "Import products",
            "",
            "CSV (*.csv);;All (*.*)",
        )
        if not path:
            return
        n_ins = n_up = n_err = 0
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                r = csv.DictReader(f)
                if not r.fieldnames:
                    warning_message(self.window(), "Import", "CSV has no header row.")
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
            warning_message(self.window(), "Import", f"Import failed: {e}")
            return
        self.refresh()
        info_message(
            self.window(),
            "Import",
            f"Import done. Added {n_ins}, updated {n_up}, skipped/errors {n_err}.",
        )
