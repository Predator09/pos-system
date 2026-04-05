"""Lightweight Tk / CustomTkinter motion — cosmetic only (no business logic)."""

from __future__ import annotations

import tkinter as tk

try:
    import customtkinter as ctk
except ImportError:
    ctk = None  # type: ignore


def animate_corner_radius_sequence(
    root: tk.Misc,
    frames: list,
    *,
    start: int = 8,
    end: int = 16,
    step: int = 2,
    delay_ms: int = 28,
) -> None:
    """Ease login / card frames from ``start`` to ``end`` corner radius (subtle entrance)."""
    if not frames or ctk is None:
        return

    def tick(r: int) -> None:
        for w in frames:
            try:
                if w.winfo_exists():
                    w.configure(corner_radius=r)
            except tk.TclError:
                return
        nr = r + step
        if nr <= end:
            root.after(delay_ms, lambda: tick(nr))

    root.after(80, lambda: tick(start))


def pulse_border_accent(
    root: tk.Misc,
    widget: tk.Widget,
    *,
    border_color: tuple[str, str],
    width: int = 2,
    hold_ms: int = 220,
    restore_width: int = 0,
) -> None:
    """Brief accent border pulse (e.g. after screen change). Restores prior border if possible."""
    if ctk is None or not hasattr(widget, "configure"):
        return
    try:
        widget.configure(border_width=width, border_color=border_color)
    except tk.TclError:
        return

    def restore() -> None:
        try:
            if widget.winfo_exists():
                widget.configure(border_width=restore_width)
        except tk.TclError:
            pass

    root.after(hold_ms, restore)


def stagger_nav_button_entrance(
    root: tk.Misc,
    nav_buttons: dict,
    key_order: list[str],
    *,
    radii: tuple[int, ...] = (4, 7, 10),
    step_ms: int = 26,
    stagger_ms: int = 38,
) -> None:
    """Soft corner-radius pop on main nav pills after login (cosmetic)."""
    if ctk is None:
        return

    def run_seq(btn, idx: int = 0) -> None:
        if idx >= len(radii):
            return
        try:
            if btn.winfo_exists():
                btn.configure(corner_radius=radii[idx])
        except tk.TclError:
            return
        root.after(step_ms, lambda: run_seq(btn, idx + 1))

    for i, key in enumerate(key_order):
        btn = nav_buttons.get(key)
        if btn is None:
            continue
        root.after(stagger_ms * i, lambda b=btn: run_seq(b, 0))
