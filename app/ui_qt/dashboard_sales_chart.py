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
from app.ui.theme_tokens import SURFACE_ELEVATED_DARK, SURFACE_ELEVATED_LIGHT, TOKENS
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
    return date.fromisoformat(key[:10]).strftime("%a %d-%m")


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
        dark_ui = bg.lightness() < 140
        muted = QColor("#8b95a8")
        # X-axis sits on the card below the plot mat — use stronger contrast than mid-gray on dark.
        axis_label = QColor("#cbd5e1" if dark_ui else "#475569")
        axis_color = QColor("#a8b0c0" if dark_ui else "#000000")
        grid = QColor(SURFACE_ELEVATED_DARK if dark_ui else SURFACE_ELEVATED_LIGHT)
        grid.setAlpha(90 if dark_ui else 140)

        n = len(self._points)
        # Always use full horizontal space so 7 d matches 30 d / 12 mo plot width (no skinny centered strip).
        plot_w = float(plot_max_w)
        x0_f = float(margin_l)
        plot_right_f = x0_f + plot_w
        min_gap, max_gap = 3.0, 10.0
        min_bar = 2.0
        if n <= 0:
            gap_f = min_gap
            bar_w_f = min_bar
        else:
            gap_f = max(min_gap, min(max_gap, 72.0 / n))
            bar_w_f = (plot_w - (n + 1) * gap_f) / n
            if bar_w_f < min_bar:
                gap_f = max(min_gap, (plot_w - n * min_bar) / (n + 1))
                bar_w_f = (plot_w - (n + 1) * gap_f) / n
            if bar_w_f < 1.0:
                bar_w_f = max(1.0, (plot_w - (n + 1) * min_gap) / n)
                gap_f = (plot_w - n * bar_w_f) / (n + 1)
        x0 = int(round(x0_f))
        plot_right = int(round(plot_right_f))
        plot_w_i = plot_right - x0
        baseline_y = margin_t + chart_h

        # Chart title (Daily / Hourly / Monthly gross) — was missing from paint; makes the view self-explanatory
        cap_font = QFont("Segoe UI", 10)
        cap_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(cap_font)
        title_pen = QColor(TOKENS.PRIMARY_HOVER if dark_ui else TOKENS.PRIMARY_MUTED)
        painter.setPen(title_pen)
        painter.drawText(margin_l, 0, w - margin_l - margin_r, 22, Qt.AlignmentFlag.AlignLeft, self._bucket_caption)

        # Soft rounded plot mat — height stops at the x-axis so labels below sit on the card, not on dark fill.
        mat = QColor(SURFACE_ELEVATED_DARK if dark_ui else SURFACE_ELEVATED_LIGHT)
        mat.setAlpha(95 if dark_ui else 185)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(mat)
        mat_h = chart_h + 3  # slight overlap for the axis stroke, no extension into tick-label band
        painter.drawRoundedRect(int(x0 - 8), int(margin_t - 2), int(plot_w_i + 16), int(mat_h), 16, 16)

        # Interior horizontal grid; baseline is the X-axis only
        painter.setPen(QPen(grid, 1, Qt.PenStyle.SolidLine))
        y_ticks = 5
        for i in range(1, y_ticks):
            frac = i / (y_ticks - 1) if y_ticks > 1 else 0.0
            gy = baseline_y - frac * chart_h
            painter.drawLine(int(x0), int(gy), int(plot_right), int(gy))

        # Y-axis spine — accent on dark; solid black on light theme for contrast on white cards
        if dark_ui:
            spine = QColor(TOKENS.PRIMARY)
            spine.setAlpha(140)
        else:
            spine = QColor("#000000")
        spine_pen = QPen(spine)
        spine_pen.setWidthF(2.0)
        painter.setPen(spine_pen)
        painter.drawLine(int(x0), int(margin_t), int(x0), int(baseline_y))

        # Bars — stronger brand gradient (hover hue → primary)
        painter.setPen(Qt.PenStyle.NoPen)
        c_top = QColor(TOKENS.PRIMARY_HOVER)
        c_top.setAlpha(235)
        c_bot = QColor(TOKENS.PRIMARY)
        c_bot.setAlpha(255)
        for i, (_key, gross) in enumerate(self._points):
            x = x0_f + gap_f + i * (bar_w_f + gap_f)
            if i == n - 1:
                bw_draw = max(1, int(round(plot_right_f - x)))
            else:
                bw_draw = max(1, int(round(bar_w_f)))
            radius = min(6, max(3, bw_draw // 2 + 1))
            bh = (gross / scale_max) * chart_h if scale_max > 0 else 0.0
            y_top = baseline_y - bh
            ibh = max(1, int(bh))
            grad = QLinearGradient(0.0, float(y_top), 0.0, float(baseline_y))
            grad.setColorAt(0.0, c_top)
            grad.setColorAt(1.0, c_bot)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(int(round(x)), int(y_top), bw_draw, ibh, radius, radius)

        # X-axis baseline
        xaxis = QPen(axis_color)
        xaxis.setWidthF(2.0)
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
        painter.setPen(axis_label)
        painter.setFont(QFont("Segoe UI", 8))
        
        if mode is _SeriesMode.HOURLY:
            # Fixed interval for hourly mode
            tick_hours = (0, 4, 8, 12, 16, 20)
            for th in tick_hours:
                if th >= n:
                    continue
                key, _ = self._points[th]
                lbl = _tick_label_x(key, mode)
                cx = x0_f + gap_f + th * (bar_w_f + gap_f) + bar_w_f / 2
                painter.drawText(int(cx - 20), int(baseline_y + 4), 40, 18, Qt.AlignmentFlag.AlignHCenter, lbl)
        else:
            # Dynamic spacing for daily/monthly modes to avoid label collisions
            min_pixel_gap = 50  # Minimum pixels between label centers
            last_drawn_x = -float('inf')
            
            for i in range(n):
                key, _ = self._points[i]
                lbl = _tick_label_x(key, mode)
                cx = x0_f + gap_f + i * (bar_w_f + gap_f) + bar_w_f / 2
                
                # Only draw if enough space from last label
                if cx - last_drawn_x >= min_pixel_gap:
                    painter.drawText(int(cx - 22), int(baseline_y + 4), 44, 18, Qt.AlignmentFlag.AlignHCenter, lbl)
                    last_drawn_x = cx
            
            # Always ensure last label is shown if there's space
            last_i = n - 1
            if n > 1:
                key, _ = self._points[last_i]
                lbl = _tick_label_x(key, mode)
                cx = x0_f + gap_f + last_i * (bar_w_f + gap_f) + bar_w_f / 2
                if cx - last_drawn_x >= min_pixel_gap:
                    painter.drawText(int(cx - 22), int(baseline_y + 4), 44, 18, Qt.AlignmentFlag.AlignHCenter, lbl)

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(muted)
        foot = f"Peak {format_money(max_g)} · scale to {_axis_money_label(scale_max)}"
        painter.drawText(margin_l, h - 14, w - margin_l - margin_r, 14, Qt.AlignmentFlag.AlignLeft, foot)