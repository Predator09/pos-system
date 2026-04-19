"""Dashboard sales trend — modernized bar chart.

Visual design: GamMarket POS teal palette, consistent with the login screen.

Improvements over original:
  • Smooth 60-fps entry animation (ease-out-cubic) on every set_data() call
  • Per-bar hover highlight with glow ring + QToolTip (exact value + date)
  • Rounded-top-only bars — flat bottom sits flush on the baseline axis
  • Peak dashed indicator line with inline label
  • Responsive left/right margins that scale with widget width
  • Inline value labels inside tall bars (no need to read Y axis)
  • Rounded card background (12px) — sits cleanly on any dashboard surface
  • Full light / dark palette auto-detection via QPalette.Window lightness
  • Graceful empty states with centred message
  • All original helper functions preserved unchanged
"""

from __future__ import annotations

import math
from datetime import date
from enum import Enum, auto

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from app.config import CURRENCY_SYMBOL
from app.ui.theme_tokens import SURFACE_ELEVATED_DARK, SURFACE_ELEVATED_LIGHT, TOKENS
from app.ui_qt.helpers_qt import format_money


# ── Design tokens (mirrors login_view.py) ──────────────────────────────────
_TEAL_ACCENT = QColor("#1DB39E")
_TEAL_MID    = QColor("#167A6A")
_TEAL_GLOW   = QColor(29, 179, 158, 38)   # accent @ ~15 % alpha

_MUTED       = QColor("#6B7280")

_AXIS_DARK   = QColor("#94A3B8")
_AXIS_LIGHT  = QColor("#374151")
_GRID_DARK   = QColor(255, 255, 255, 18)
_GRID_LIGHT  = QColor(0, 0, 0, 10)
_CARD_DARK   = QColor("#132E2B")
_CARD_LIGHT  = QColor("#FFFFFF")

# Animation
_ANIM_STEPS  = 24    # total frames
_ANIM_MS     = 16    # ≈ 60 fps


# ── Helpers (unchanged from original) ─────────────────────────────────────

class _SeriesMode(Enum):
    HOURLY  = auto()
    DAILY   = auto()
    MONTHLY = auto()


def _detect_mode(first_key: str) -> _SeriesMode:
    if not first_key:
        return _SeriesMode.DAILY
    if len(first_key) == 13 and first_key[10] == "T":
        return _SeriesMode.HOURLY
    if len(first_key) == 7 and first_key[4] == "-":
        return _SeriesMode.MONTHLY
    return _SeriesMode.DAILY


def _tick_label_x(key: str, mode: _SeriesMode) -> str:
    try:
        if mode is _SeriesMode.MONTHLY:
            y, m = key.split("-")
            return date(int(y), int(m), 1).strftime("%b '%y")
        if mode is _SeriesMode.HOURLY:
            h = int(key.split("T")[1])
            if h == 0:  return "12a"
            if h < 12:  return f"{h}a"
            if h == 12: return "12p"
            return f"{h - 12}p"
        return date.fromisoformat(key[:10]).strftime("%a %d-%m")
    except Exception:
        return key


def _nice_ceiling_scale(max_val: float) -> float:
    if max_val <= 0:
        return 1.0
    exp  = math.floor(math.log10(max_val))
    frac = max_val / (10 ** exp)
    for nice in (1.0, 2.0, 2.5, 5.0, 10.0):
        if frac <= nice:
            return nice * (10 ** exp)
    return 10.0 * (10 ** exp)


def _axis_money_label(amount: float) -> str:
    sym = CURRENCY_SYMBOL
    a   = abs(amount)
    if a >= 1_000_000:
        return f"{sym}{amount / 1_000_000:.1f}M"
    if a >= 1_000:
        return f"{sym}{amount / 1_000:.1f}k"
    return format_money(amount)


# ── Easing ─────────────────────────────────────────────────────────────────

def _ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


# ── Widget ─────────────────────────────────────────────────────────────────

class DashboardSalesChart(QWidget):
    """Modern animated sales bar chart — no QtCharts dependency."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._points:         list[tuple[str, float]] = []
        self._bucket_caption: str = ""

        # animation
        self._anim_step  = _ANIM_STEPS          # start "done" (no flash on first show)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(_ANIM_MS)
        self._anim_timer.timeout.connect(self._anim_tick)

        # hover
        self._hovered_bar: int        = -1
        self._bar_rects:  list[QRect] = []

        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.setMouseTracking(True)

    # ── Public API ──────────────────────────────────────────────────────────

    def set_data(self, points: list[tuple[str, float]], caption: str = "") -> None:
        self._points         = points or []
        self._bucket_caption = caption or ""
        self._hovered_bar    = -1
        self._bar_rects      = []
        # kick off entry animation
        self._anim_step = 0
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    # ── Animation ───────────────────────────────────────────────────────────

    def _anim_tick(self) -> None:
        self._anim_step += 1
        self.update()
        if self._anim_step >= _ANIM_STEPS:
            self._anim_timer.stop()

    def _progress(self) -> float:
        return _ease_out_cubic(min(1.0, self._anim_step / _ANIM_STEPS))

    # ── Mouse ────────────────────────────────────────────────────────────────

    def mouseMoveEvent(self, event) -> None:
        pos  = event.pos()
        prev = self._hovered_bar
        self._hovered_bar = -1

        for i, rect in enumerate(self._bar_rects):
            col = QRect(rect.x(), 0, rect.width(), self.height())
            if col.contains(pos):
                self._hovered_bar = i
                if self._points:
                    key, val = self._points[i]
                    mode  = _detect_mode(self._points[0][0])
                    label = _tick_label_x(key, mode)
                    QToolTip.showText(
                        event.globalPos(),
                        f"<b>{label}</b><br>{format_money(val)}",
                        self,
                    )
                break

        if self._hovered_bar != prev:
            self.update()

    def leaveEvent(self, event) -> None:
        self._hovered_bar = -1
        self.update()

    # ── Paint ────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: C901
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        W, H = self.width(), self.height()

        # theme
        bg   = self.palette().color(QPalette.Window)
        dark = bg.lightness() < 140
        axis_color  = _AXIS_DARK  if dark else _AXIS_LIGHT
        grid_color  = _GRID_DARK  if dark else _GRID_LIGHT
        card_color  = _CARD_DARK  if dark else _CARD_LIGHT
        muted_color = _AXIS_DARK  if dark else _MUTED

        # responsive margins
        margin_l = max(54, min(82, W // 9))
        margin_r = max(14, W // 44)
        margin_t = 38
        margin_b = 44

        chart_h = max(1, H - margin_t - margin_b)
        plot_w  = max(1, W - margin_l - margin_r)
        x0      = margin_l
        base_y  = margin_t + chart_h

        # card background
        painter.setPen(Qt.NoPen)
        painter.setBrush(card_color)
        card_path = QPainterPath()
        card_path.addRoundedRect(0, 0, W, H, 12, 12)
        painter.drawPath(card_path)

        # ── empty states ──────────────────────────────────────────────────
        if not self._points:
            painter.setPen(muted_color)
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(0, 0, W, H, Qt.AlignCenter, "No data available")
            return

        max_val = max(v for _, v in self._points)
        if max_val <= 0:
            painter.setPen(muted_color)
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(0, 0, W, H, Qt.AlignCenter, "No sales recorded")
            return

        mode      = _detect_mode(self._points[0][0])
        scale_max = _nice_ceiling_scale(max_val)
        prog      = self._progress()
        n         = len(self._points)

        # bar sizing
        gap   = max(3, min(12, plot_w / max(1, n * 5)))
        bar_w = max(4.0, (plot_w - gap * (n + 1)) / n)

        # ── grid ──────────────────────────────────────────────────────────
        Y_TICKS = 5
        painter.setPen(QPen(grid_color, 1))
        for i in range(1, Y_TICKS):
            gy = int(base_y - (i / (Y_TICKS - 1)) * chart_h)
            painter.drawLine(x0, gy, x0 + plot_w, gy)

        # ── peak dashed line ──────────────────────────────────────────────
        peak_y = base_y - (max_val / scale_max) * chart_h * prog
        dash_pen = QPen(_TEAL_ACCENT, 1, Qt.DashLine)
        dash_pen.setDashPattern([4, 4])
        painter.setPen(dash_pen)
        painter.drawLine(x0, int(peak_y), x0 + plot_w, int(peak_y))

        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        painter.setPen(_TEAL_ACCENT)
        painter.drawText(
            x0 + 4, int(peak_y) - 15,
            plot_w - 8, 14,
            Qt.AlignRight | Qt.AlignVCenter,
            f"Peak  {format_money(max_val)}",
        )

        # ── bars ──────────────────────────────────────────────────────────
        self._bar_rects = []

        for i, (key, val) in enumerate(self._points):
            bx     = int(x0 + gap + i * (bar_w + gap))
            full_h = (val / scale_max) * chart_h
            anim_h = max(2.0, full_h * prog)
            by     = int(base_y - anim_h)
            bh     = int(anim_h)
            bw     = int(bar_w)

            self._bar_rects.append(QRect(bx, by, bw, bh))
            hovered = (i == self._hovered_bar)

            # glow ring on hover
            if hovered:
                glow_path = QPainterPath()
                glow_path.addRoundedRect(bx - 3, by - 3, bw + 6, bh + 6, 7, 7)
                painter.setPen(Qt.NoPen)
                painter.setBrush(_TEAL_GLOW)
                painter.drawPath(glow_path)

            # gradient fill
            grad = QLinearGradient(0, by, 0, base_y)
            if hovered:
                grad.setColorAt(0, _TEAL_ACCENT.lighter(118))
                grad.setColorAt(1, _TEAL_MID.lighter(112))
            else:
                grad.setColorAt(0, _TEAL_ACCENT)
                grad.setColorAt(1, _TEAL_MID)

            # rounded-top-only path
            bar_path = QPainterPath()
            r = min(5, bw // 2, bh // 2)
            bar_path.moveTo(bx, base_y)
            bar_path.lineTo(bx, by + r)
            bar_path.quadTo(bx, by, bx + r, by)
            bar_path.lineTo(bx + bw - r, by)
            bar_path.quadTo(bx + bw, by, bx + bw, by + r)
            bar_path.lineTo(bx + bw, base_y)
            bar_path.closeSubpath()

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawPath(bar_path)

            # inline value label (only when bar is large enough)
            if bh > 28 and bw > 32:
                painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(
                    bx, by + 4, bw, 16,
                    Qt.AlignHCenter | Qt.AlignTop,
                    _axis_money_label(val),
                )

        # ── baseline axis ──────────────────────────────────────────────────
        painter.setPen(QPen(axis_color, 1.5))
        painter.drawLine(x0, base_y, x0 + plot_w, base_y)

        # ── Y labels ──────────────────────────────────────────────────────
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(muted_color)
        for i in range(Y_TICKS):
            gy  = int(base_y - (i / (Y_TICKS - 1)) * chart_h)
            val = scale_max * (i / (Y_TICKS - 1))
            painter.drawText(
                0, gy - 8,
                margin_l - 8, 16,
                Qt.AlignRight | Qt.AlignVCenter,
                _axis_money_label(val),
            )

        # ── X labels ──────────────────────────────────────────────────────
        painter.setPen(axis_color)
        painter.setFont(QFont("Segoe UI", 8))
        fm      = QFontMetrics(painter.font())
        last_lx = -999
        min_gap = 46

        for i, (key, _) in enumerate(self._points):
            cx  = int(x0 + gap + i * (bar_w + gap) + bar_w / 2)
            lbl = _tick_label_x(key, mode)
            lw  = fm.horizontalAdvance(lbl)

            # always draw the last label; skip crowded intermediate ones
            is_last = (i == n - 1)
            if not is_last and cx - last_lx < min_gap:
                continue

            painter.drawText(
                cx - lw // 2,
                base_y + 7,
                lw + 4, 18,
                Qt.AlignHCenter,
                lbl,
            )
            last_lx = cx

        # ── caption ───────────────────────────────────────────────────────
        if self._bucket_caption:
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(muted_color)
            painter.drawText(
                x0, H - 16,
                plot_w, 16,
                Qt.AlignLeft | Qt.AlignVCenter,
                self._bucket_caption,
            )

        painter.end()