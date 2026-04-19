"""Small helpers to apply qtawesome icons with graceful fallback."""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QDialogButtonBox, QLabel, QPushButton, QStyle

try:
    import qtawesome as qta
except Exception:  # pragma: no cover - optional dependency fallback
    qta = None


def set_button_icon(
    button: QPushButton,
    icon_name: str,
    *,
    color: str | None = None,
    size: int | None = None,
) -> None:
    """Set a qtawesome icon if available; silently keep text if unavailable.

    Consistency rules:
    - color defaults to the button's current text color (theme-aware),
    - icon size scales with control height,
    - sets a dynamic property used by QSS for icon/text spacing.
    """
    if qta is None:
        return
    try:
        resolved_color = color or button.palette().buttonText().color().name()
        resolved_size = size or (18 if button.minimumHeight() >= 40 else 16)
        icon = qta.icon(icon_name, color=resolved_color)
        button.setIcon(icon)
        button.setIconSize(QSize(resolved_size, resolved_size))
        button.setProperty("hasIcon", True)
        # Re-polish so the QSS selector ``[hasIcon="true"]`` applies immediately.
        st: QStyle | None = button.style()
        if st is not None:
            st.unpolish(button)
            st.polish(button)
    except Exception:
        # Keep UX functional even if a specific icon name is not present.
        return


def set_label_icon(
    label: QLabel,
    icon_name: str,
    *,
    color: str = "#64748b",
    size: int = 20,
) -> None:
    """Apply a qtawesome pixmap to a QLabel; no-op if qtawesome is unavailable."""
    if qta is None:
        return
    try:
        icon = qta.icon(icon_name, color=color)
        label.setPixmap(icon.pixmap(QSize(size, size)))
        label.setFixedSize(size, size)
        label.setScaledContents(False)
    except Exception:
        return


def style_dialog_button_box(
    box: QDialogButtonBox,
    *,
    ok_icon: str = "fa5s.check-circle",
    cancel_icon: str = "fa5s.times",
    ok_primary: bool = True,
) -> None:
    """Apply consistent icon/styling to common dialog action buttons."""
    ok_btn = (
        box.button(QDialogButtonBox.StandardButton.Ok)
        or box.button(QDialogButtonBox.StandardButton.Save)
        or box.button(QDialogButtonBox.StandardButton.Apply)
    )
    cancel_btn = (
        box.button(QDialogButtonBox.StandardButton.Cancel)
        or box.button(QDialogButtonBox.StandardButton.Close)
    )
    if ok_btn is not None:
        if ok_primary:
            ok_btn.setObjectName("primary")
        set_button_icon(ok_btn, ok_icon)
    if cancel_btn is not None:
        set_button_icon(cancel_btn, cancel_icon)

