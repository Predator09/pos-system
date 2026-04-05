"""Compatibility shims for CustomTkinter + Tkinter (e.g. Python 3.14).

CustomTkinter's scaling tracker calls ``block_update_dimensions_event`` /
``unblock_update_dimensions_event`` on the root window. On some CPython/Tk
builds these are not exposed on ``_tkinter.tkapp``, so attribute lookup fails.

Apply **before** ``import customtkinter``.
"""

from __future__ import annotations

import tkinter as tk


def apply_customtkinter_tkinter_shim() -> None:
    def _noop(self: tk.Misc) -> None:
        return None

    for cls in (tk.Tk, tk.Toplevel):
        if not hasattr(cls, "block_update_dimensions_event"):
            cls.block_update_dimensions_event = _noop  # type: ignore[method-assign]
        if not hasattr(cls, "unblock_update_dimensions_event"):
            cls.unblock_update_dimensions_event = _noop  # type: ignore[method-assign]
