"""Shop logo: click to set image, context menu to remove (uses ShopSettings)."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCursor, QPixmap
from PySide6.QtWidgets import QFileDialog, QLabel, QMenu

from app.services.shop_settings import ShopSettings


class ShopLogoLabel(QLabel):
    def __init__(self, parent=None, *, size: int = 72, editable: bool = True):
        super().__init__(parent)
        self._size = size
        self._editable = editable
        self._settings = ShopSettings()
        self.setObjectName("shopLogo")
        self.setFixedSize(size + 8, size + 8)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor if editable else Qt.ArrowCursor)
        self.refresh()

    def _polish_logo_state(self) -> None:
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)

    def refresh(self) -> None:
        path = self._settings.get_logo_path()
        if path and Path(path).is_file():
            pm = QPixmap(path)
            if not pm.isNull():
                pm = pm.scaled(self._size, self._size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.setPixmap(pm)
                self.setText("")
                self.setProperty("logoState", "image")
                self._polish_logo_state()
                return
        self.clear()
        self.setText("+")
        self.setProperty("logoState", "empty")
        self._polish_logo_state()

    def mousePressEvent(self, event):
        if not self._editable:
            return super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Choose shop logo",
                "",
                "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp);;All (*.*)",
            )
            if path:
                try:
                    self._settings.set_logo_from_file(path)
                    self.refresh()
                except Exception as e:
                    from app.ui_qt.helpers_qt import warning_message

                    warning_message(self, "Logo", str(e))
        elif event.button() == Qt.RightButton and self._settings.get_logo_path():
            menu = QMenu(self)
            act = QAction("Remove logo", self)
            act.triggered.connect(self._remove)
            menu.addAction(act)
            menu.exec(QCursor.pos())
        super().mousePressEvent(event)

    def _remove(self) -> None:
        self._settings.clear_logo()
        self.refresh()
