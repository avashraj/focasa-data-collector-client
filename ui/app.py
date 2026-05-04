import threading
import tkinter as tk
from typing import Optional

import api.client as client
import core.storage as storage
from core.background import ScreenshotService
from core.device import get_device_name, get_os
from ui.home_screen import HomeScreen
from ui.setup_screen import SetupScreen


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Focasa")
        self.resizable(False, False)
        self.geometry("360x320")
        self._center()
        self._screenshot_service: Optional[ScreenshotService] = None
        self._api_key: Optional[str] = None
        self._user_id: Optional[str] = None
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start()

    def start_screenshot_service(self) -> None:
        active = storage.load_active_task()
        if not active or not self._api_key or not self._user_id:
            return
        self.stop_screenshot_service()
        self._screenshot_service = ScreenshotService(
            api_key=self._api_key,
            user_id=self._user_id,
            task_id=active["task_id"],
        )
        self._screenshot_service.start()

    def stop_screenshot_service(self) -> None:
        if self._screenshot_service is not None:
            self._screenshot_service.stop()
            self._screenshot_service = None

    def _center(self):
        self.update_idletasks()
        w, h = 360, 320
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _start(self):
        config = storage.load_config()
        if config:
            if storage.load_active_task():
                self.start_screenshot_service()
            self._verify_and_start(config)
        else:
            self._show_setup()

    def _verify_and_start(self, config: dict):
        self._clear()
        label = tk.Label(self, text="Verifying…", font=("Helvetica", 13), fg="#888888")
        label.place(relx=0.5, rely=0.5, anchor="center")
        threading.Thread(target=self._do_verify, args=(config,), daemon=True).start()

    def _do_verify(self, config: dict):
        try:
            client.register(
                api_key=config["api_key"],
                user_id=config["user_id"],
                device_name=get_device_name(),
                os_name=get_os(),
            )
            self.after(0, lambda: self._show_home(config["user_id"], config["api_key"]))
        except Exception:
            self.after(
                0,
                lambda: self._show_setup(
                    "API key invalid or expired. Please re-enter."
                ),
            )

    def _show_setup(self, initial_error: str = ""):
        self._clear()
        frame = SetupScreen(
            self, on_success=self._show_home, initial_error=initial_error
        )
        frame.pack(fill="both", expand=True)

    def _show_home(self, user_id: str, api_key: str):
        self._user_id = user_id
        self._api_key = api_key
        self._clear()
        frame = HomeScreen(
            self,
            user_id=user_id,
            api_key=api_key,
            on_auth_error=self._show_setup,
            on_task_start=self.start_screenshot_service,
            on_task_end=self.stop_screenshot_service,
        )
        frame.pack(fill="both", expand=True)

    def _on_close(self):
        self.stop_screenshot_service()
        self.destroy()

    def _clear(self):
        for widget in self.winfo_children():
            widget.destroy()
