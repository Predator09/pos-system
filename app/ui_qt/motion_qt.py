"""Qt property animations — UI-only (no business logic)."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


def fade_in_widget(widget: QWidget, duration_ms: int = 280, *, start: float = 0.0, end: float = 1.0) -> None:
    """Opacity 0→1 with an ease-out curve. Replaces any existing graphics effect."""
    if widget is None:
        return
    eff = QGraphicsOpacityEffect(widget)
    eff.setOpacity(start)
    widget.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(int(duration_ms))
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.finished.connect(lambda: _maybe_clear_effect(widget, eff, end))
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def _maybe_clear_effect(widget: QWidget, eff: QGraphicsOpacityEffect, end: float) -> None:
    if end >= 0.99 and widget.graphicsEffect() is eff:
        widget.setGraphicsEffect(None)
