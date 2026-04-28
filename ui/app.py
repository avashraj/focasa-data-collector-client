import tkinter as tk

import core.storage as storage
from ui.setup_screen import SetupScreen
from ui.home_screen import HomeScreen


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Focasa")
        self.resizable(False, False)
        self.geometry("360x320")
        self._center()
        self._start()

    def _center(self):
        self.update_idletasks()
        w, h = 360, 320
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _start(self):
        config = storage.load_config()
        if config:
            self._show_home(config["user_id"])
        else:
            self._show_setup()

    def _show_setup(self):
        self._clear()
        frame = SetupScreen(self, on_success=self._show_home)
        frame.pack(fill="both", expand=True)

    def _show_home(self, user_id: str):
        self._clear()
        frame = HomeScreen(self, user_id=user_id)
        frame.pack(fill="both", expand=True)

    def _clear(self):
        for widget in self.winfo_children():
            widget.destroy()
