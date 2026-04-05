"""Simple bar chart for dashboard sales overview (no QtCharts dependency)."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPalette
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.ui.theme_tokens import TOKENS
from app.ui_qt.helpers_qt import format_money


def _tick_label_x(key: str, *, monthly: bool) -> str:
    if monthly:
        y, m = key.split("-")
        return date(int(y), int(m), 1).strftime("%b '%y")
    return date.fromisoformat(key[:10]).strftime("%a %d")


class DashboardSalesChart(QWidget):
    """Bar chart for (label, gross) points; updates via ``set_data``."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[tuple[str, float]] = []
        self._bucket_caption = ""
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

    def set_data(self, points: list[tuple[str, float]], caption: str) -> None:
        self._points = list(points)
        self._bucket_caption = caption
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin_l, margin_r, margin_t, margin_b = 40, 10, 22, 30
        chart_w = max(1, w - margin_l - margin_r)
        chart_h = max(1, h - margin_t - margin_b)

        bg = self.palette().color(QPalette.ColorRole.Window)
        painter.fillRect(self.rect(), bg)

        if not self._points:
            painter.setPen(QColor("#8b95a8"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data for this range")
            return

        max_g = max(v for _, v in self._points)
        if max_g <= 0:
            painter.setPen(QColor("#8b95a8"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No sales in this period")
            return

        monthly = "-" in self._points[0][0] and len(self._points[0][0]) == 7

        accent = QColor(TOKENS.PRIMARY)
        muted = QColor("#8b95a8")
        grid = QColor("#304560" if bg.lightness() < 140 else "#cbd5e1")

        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))
        for i in range(1, 4):
            gy = margin_t + chart_h * (1.0 - i / 4.0)
            painter.drawLine(margin_l, int(gy), margin_l + chart_w, int(gy))

        n = len(self._points)
        gap = max(2, min(6, chart_w // (n * 4)))
        bar_w = max(3, (chart_w - gap * (n + 1)) // n)

        painter.setPen(Qt.PenStyle.NoPen)
        for i, (_key, gross) in enumerate(self._points):
            x = margin_l + gap + i * (bar_w + gap)
            bh = (gross / max_g) * chart_h
            y = margin_t + chart_h - bh
            painter.setBrush(accent)
            painter.drawRoundedRect(int(x), int(y), int(bar_w), max(1, int(bh)), 3, 3)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(muted)
        painter.setFont(QFont("Segoe UI", 8))
        step = max(1, (n + 7) // 8)
        for i in range(0, n, step):
            key, _ = self._points[i]
            lbl = _tick_label_x(key, monthly=monthly)
            x = margin_l + gap + i * (bar_w + gap) + bar_w / 2
            painter.drawText(int(x - 22), h - 8, 44, 20, Qt.AlignmentFlag.AlignHCenter, lbl)

        cap_font = QFont("Segoe UI", 9)
        cap_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(cap_font)
        painter.setPen(muted)
        painter.drawText(margin_l, 4, chart_w, 18, Qt.AlignmentFlag.AlignLeft, self._bucket_caption)
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(
            margin_l,
            margin_t + chart_h + 2,
            chart_w,
            14,
            Qt.AlignmentFlag.AlignRight,
            f"Max {format_money(max_g)}",
        )
