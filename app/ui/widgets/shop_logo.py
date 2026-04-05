"""Circular shop logo: click to set image, right-click to remove."""

import tkinter as tk
from tkinter import filedialog, Menu

import ttkbootstrap as ttk
from PIL import Image, ImageDraw, ImageTk

from app.services.shop_settings import ShopSettings
from app.ui.helpers import show_message


class ShopLogoWidget(ttk.Frame):
    def __init__(self, parent, size: int = 72, editable: bool = True):
        super().__init__(parent)
        self._size = size
        self._editable = editable
        self._settings = ShopSettings()
        self._photo = None

        pad = 4
        self._canvas = tk.Canvas(
            self,
            width=size + pad * 2,
            height=size + pad * 2,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack()

        if editable:
            self._canvas.bind("<Button-1>", self._on_click)
            self._canvas.bind("<Button-3>", self._on_right_click)

        self._draw_placeholder()

    def _canvas_bg(self) -> str:
        try:
            bg = ttk.Style().lookup("TFrame", "background")
            if bg:
                return bg
        except tk.TclError:
            pass
        try:
            return self.winfo_toplevel().cget("background")
        except tk.TclError:
            return "#2b3e50"

    def _circular_photo(self, path: str) -> ImageTk.PhotoImage | None:
        try:
            img = Image.open(path).convert("RGBA")
            img = img.resize((self._size, self._size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (self._size, self._size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, self._size - 1, self._size - 1), fill=255)
            out = Image.new("RGBA", (self._size, self._size), (0, 0, 0, 0))
            out.paste(img, (0, 0), mask)
            self._photo = ImageTk.PhotoImage(out)
            return self._photo
        except OSError:
            return None

    def _draw_placeholder(self):
        self._canvas.delete("all")
        bg = self._canvas_bg()
        self._canvas.config(bg=bg)
        pad = 4
        x0, y0 = pad, pad
        x1, y1 = pad + self._size, pad + self._size
        self._canvas.create_oval(x0, y0, x1, y1, outline="#666666", width=2, fill="#3a3a3a")
        hint = "Add" if self._editable else ""
        if hint:
            self._canvas.create_text(
                (pad + self._size // 2, pad + self._size // 2),
                text=hint,
                fill="#aaaaaa",
                font=("Helvetica", 10),
            )

    def refresh(self):
        self._photo = None
        path = self._settings.get_logo_path()
        self._canvas.delete("all")
        bg = self._canvas_bg()
        self._canvas.config(bg=bg)
        pad = 4
        x0, y0 = pad, pad
        x1, y1 = pad + self._size, pad + self._size

        if path:
            photo = self._circular_photo(path)
            if photo:
                self._canvas.create_oval(x0 - 1, y0 - 1, x1 + 1, y1 + 1, outline="#888888", width=2)
                self._canvas.create_image(pad + self._size // 2, pad + self._size // 2, image=photo)
                return

        self._draw_placeholder()

    def _on_click(self, event):
        if not self._editable:
            return
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Choose shop logo",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.webp *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            self._settings.set_logo_from_file(path)
            self.refresh()
        except Exception as e:
            show_message(f"Could not set logo: {e}", parent=self.winfo_toplevel())

    def _on_right_click(self, event):
        if not self._editable:
            return
        if not self._settings.get_logo_path():
            return
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Remove logo", command=self._remove_logo)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _remove_logo(self):
        self._settings.clear_logo()
        self.refresh()
