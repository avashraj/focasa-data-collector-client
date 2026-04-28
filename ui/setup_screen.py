import tkinter as tk
from tkinter import ttk
import threading
import uuid

import api.client as client
import core.storage as storage
from core.device import get_os, get_device_name


class SetupScreen(tk.Frame):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self._on_success = on_success
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

        title = tk.Label(self, text="Focasa", font=("Helvetica", 22, "bold"))
        title.grid(row=0, column=0, pady=(40, 4))

        subtitle = tk.Label(
            self,
            text="Enter your API key to get started",
            font=("Helvetica", 12),
            fg="#555555",
        )
        subtitle.grid(row=1, column=0, pady=(0, 24))

        self._api_key_var = tk.StringVar()
        entry = ttk.Entry(self, textvariable=self._api_key_var, width=36, show="")
        entry.grid(row=2, column=0, ipady=6, pady=(0, 12))
        entry.focus()
        entry.bind("<Return>", lambda _: self._submit())

        self._submit_btn = ttk.Button(self, text="Register Device", command=self._submit)
        self._submit_btn.grid(row=3, column=0, pady=(0, 12))

        self._error_label = tk.Label(self, text="", fg="#cc0000", wraplength=280)
        self._error_label.grid(row=4, column=0, pady=(0, 20))

    def _submit(self):
        api_key = self._api_key_var.get().strip()
        if not api_key:
            self._show_error("Please enter an API key.")
            return

        self._show_error("")
        self._submit_btn.config(state="disabled", text="Registering...")
        threading.Thread(target=self._do_register, args=(api_key,), daemon=True).start()

    def _do_register(self, api_key: str):
        try:
            existing = storage.load_config()
            user_id = existing["user_id"] if existing else str(uuid.uuid4())
            result = client.register(
                api_key=api_key,
                user_id=user_id,
                device_name=get_device_name(),
                os_name=get_os(),
            )
            confirmed_id = result.get("user_id") or result.get("id") or user_id
            storage.save_config(api_key=api_key, user_id=confirmed_id)
            self.after(0, lambda uid=confirmed_id: self._on_success(uid))
        except Exception as exc:
            self.after(0, lambda e=exc: self._handle_error(e))

    def _handle_error(self, exc: Exception):
        self._submit_btn.config(state="normal", text="Register Device")
        self._show_error(f"Registration failed: {exc}")

    def _show_error(self, message: str):
        self._error_label.config(text=message)
