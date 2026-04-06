"""Dashboard sales trend: bar chart with axes, grid, and sensible bucketing (no QtCharts)."""

from __future__ import annotations

import math
from datetime import date
from enum import Enum, auto

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPalette,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.config import CURRENCY_SYMBOL
from app.ui.theme_tokens import TOKENS
from app.ui_qt.helpers_qt import format_money


class _SeriesMode(Enum):
    HOURLY = auto()
    DAILY = auto()
    MONTHLY = auto()


def _detect_mode(first_key: str) -> _SeriesMode:
    k = first_key or ""
    if len(k) == 13 and k[10] == "T" and k[11:13].isdigit():
        return _SeriesMode.HOURLY
    if len(k) == 7 and k[4] == "-" and k[:4].isdigit() and k[5:7].isdigit():
        return _SeriesMode.MONTHLY
    return _SeriesMode.DAILY


def _tick_label_x(key: str, mode: _SeriesMode) -> str:
    if mode is _SeriesMode.MONTHLY:
        y, m = key.split("-")
        return date(int(y), int(m), 1).strftime("%b '%y")
    if mode is _SeriesMode.HOURLY:
        h = int(key.split("T", 1)[1])
        if h == 0:
            return "12a"
        if h < 12:
            return f"{h}a"
        if h == 12:
            return "12p"
        return f"{h - 12}p"
    return date.fromisoformat(key[:10]).strftime("%a %d")


def _nice_ceiling_scale(max_val: float) -> float:
    """Upper bound for Y-axis so grid lines land on round amounts."""
    if max_val <= 0:
        return 1.0
    if max_val < 1e-9:
        return 1.0
    exp = math.floor(math.log10(max_val))
    frac = max_val / (10**exp)
    for nice in (1.0, 2.0, 2.5, 5.0, 10.0):
        if frac <= nice:
            return nice * (10**exp)
    return 10.0 * (10**exp)


def _axis_money_label(amount: float) -> str:
    """Shorter Y-axis tick labels when values are large (uses app currency)."""
    a = abs(amount)
    sym = CURRENCY_SYMBOL
    if a >= 1_000_000:
        return f"{sym} {amount / 1_000_000:.1f}M"
    if a >= 10_000:
        return f"{sym} {amount / 1_000:.0f}k"
    if a >= 1_000:
        return f"{sym} {amount / 1_000:.1f}k"
    return format_money(amount)


class DashboardSalesChart(QWidget):
    """Bar chart for (label, gross) points; updates via ``set_data``."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardSalesChart")
        self._points: list[tuple[str, float]] = []
        self._bucket_caption = ""
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setAutoFillBackground(False)

    def set_data(self, points: list[tuple[str, float]], caption: str) -> None:
        self._points = list(points)
        self._bucket_caption = caption
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin_l, margin_r, margin_t, margin_b = 66, 14, 26, 36
        plot_max_w = max(1, w - margin_l - margin_r)
        chart_h = max(1, h - margin_t - margin_b)

        bg = self.palette().color(QPalette.ColorRole.Window)

        if not self._points:
            painter.setPen(QColor("#8b95a8"))
            painter.drawText(
                margin_l,
                0,
                w - margin_l - margin_r,
                h,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "No data for this range",
            )
            return

        max_g = max(v for _, v in self._points)
        if max_g <= 0:
            painter.setPen(QColor("#8b95a8"))
            painter.drawText(
                margin_l,
                0,
                w - margin_l - margin_r,
                h,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "No sales in this period",
            )
            return

        mode = _detect_mode(self._points[0][0])
        scale_max = _nice_ceiling_scale(max_g)
        accent = QColor(TOKENS.PRIMARY)
        dark_ui = bg.lightness() < 140
        muted = QColor("#8b95a8")
        axis_color = QColor("#a8b0c0" if dark_ui else "#64748b")
        grid = QColor("#283548" if dark_ui else "#e2e8f0")
        grid.setAlpha(90 if dark_ui else 140)

        n = len(self._points)
        gap = max(3, min(10, int(72 / max(n, 1))))
        bar_w = max(4, 14)
        plot_w = n * bar_w + (n + 1) * gap
        if plot_w > plot_max_w:
            bar_w = max(2, (plot_max_w - gap * (n + 1)) // n)
            plot_w = n * bar_w + (n + 1) * gap
        plot_w = min(plot_w, plot_max_w)
        x0 = margin_l
        plot_right = x0 + plot_w
        baseline_y = margin_t + chart_h

        # Metric name is implied by the Sales trend section + range pills; Y-axis shows amounts.

        # Interior horizontal grid only (no border box); skip baseline — drawn as X-axis
        painter.setPen(QPen(grid, 1, Qt.PenStyle.SolidLine))
        y_ticks = 5
        for i in range(1, y_ticks):
            frac = i / (y_ticks - 1) if y_ticks > 1 else 0.0
            gy = baseline_y - frac * chart_h
            painter.drawLine(int(x0), int(gy), int(plot_right), int(gy))

        # Y-axis spine (open chart, not a frame)
        spine_pen = QPen(axis_color)
        spine_pen.setWidthF(1.25)
        painter.setPen(spine_pen)
        painter.drawLine(int(x0), int(margin_t), int(x0), int(baseline_y))

        # Bars — soft vertical gradient, rounded top
        painter.setPen(Qt.PenStyle.NoPen)
        radius = min(5, max(2, bar_w // 2))
        top_hi = QColor(accent)
        top_hi.setAlpha(215)
        bot = QColor(accent)
        bot.setAlpha(255)
        for i, (_key, gross) in enumerate(self._points):
            x = x0 + gap + i * (bar_w + gap)
            bh = (gross / scale_max) * chart_h if scale_max > 0 else 0.0
            y_top = baseline_y - bh
            ibh = max(1, int(bh))
            grad = QLinearGradient(0.0, float(y_top), 0.0, float(baseline_y))
            grad.setColorAt(0.0, top_hi)
            grad.setColorAt(1.0, bot)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(int(x), int(y_top), int(bar_w), ibh, radius, radius)

        # X-axis baseline (slightly stronger than grid)
        xaxis = QPen(axis_color)
        xaxis.setWidthF(1.5)
        painter.setPen(xaxis)
        painter.drawLine(int(x0), int(baseline_y), int(plot_right), int(baseline_y))

        # Y tick labels
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(muted)
        for i in range(y_ticks):
            frac = i / (y_ticks - 1) if y_ticks > 1 else 0.0
            gy = baseline_y - frac * chart_h
            val = scale_max * frac
            lbl = _axis_money_label(val)
            painter.drawText(2, int(gy - 8), margin_l - 10, 16, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, lbl)

        # X tick labels with smart spacing to avoid collisions
        painter.setPen(muted)
        painter.setFont(QFont("Segoe UI", 8))
        
        if mode is _SeriesMode.HOURLY:
            # Fixed interval for hourly mode
            tick_hours = (0, 4, 8, 12, 16, 20)
            for th in tick_hours:
                if th >= n:
                    continue
                key, _ = self._points[th]
                lbl = _tick_label_x(key, mode)
                cx = x0 + gap + th * (bar_w + gap) + bar_w / 2
                painter.drawText(int(cx - 20), int(baseline_y + 4), 40, 18, Qt.AlignmentFlag.AlignHCenter, lbl)
        else:
            # Dynamic spacing for daily/monthly modes to avoid label collisions
            min_pixel_gap = 50  # Minimum pixels between label centers
            last_drawn_x = -float('inf')
            
            for i in range(n):
                key, _ = self._points[i]
                lbl = _tick_label_x(key, mode)
                cx = x0 + gap + i * (bar_w + gap) + bar_w / 2
                
                # Only draw if enough space from last label
                if cx - last_drawn_x >= min_pixel_gap:
                    painter.drawText(int(cx - 22), int(baseline_y + 4), 44, 18, Qt.AlignmentFlag.AlignHCenter, lbl)
                    last_drawn_x = cx
            
            # Always ensure last label is shown if there's space
            last_i = n - 1
            if n > 1:
                key, _ = self._points[last_i]
                lbl = _tick_label_x(key, mode)
                cx = x0 + gap + last_i * (bar_w + gap) + bar_w / 2
                if cx - last_drawn_x >= min_pixel_gap:
                    painter.drawText(int(cx - 22), int(baseline_y + 4), 44, 18, Qt.AlignmentFlag.AlignHCenter, lbl)