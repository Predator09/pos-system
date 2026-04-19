"""Reusable Qt card containers for dashboard-style surfaces."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout


class CardFrame(QFrame):
    """Standard card surface with consistent spacing and rounded shape."""

    def __init__(
        self,
        parent=None,
        *,
        object_name: str = "card",
        padding: tuple[int, int, int, int] = (16, 14, 16, 14),
        spacing: int = 8,
    ):
        super().__init__(parent)
        self.setObjectName(object_name)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(*padding)
        lay.setSpacing(spacing)
        self.content_layout = lay

