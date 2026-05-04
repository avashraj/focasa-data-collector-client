import threading
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

import tkinter as tk
from tkinter import ttk

import api.client as client
import core.storage as storage

_RETRY_BASE_MS = 2_000
_RETRY_MAX_MS = 30_000


class HomeScreen(tk.Frame):
    def __init__(
        self,
        parent,
        user_id: str,
        api_key: str,
        on_auth_error: Callable[[str], None],
        on_task_start: Callable[[], None] = lambda: None,
        on_task_end: Callable[[], None] = lambda: None,
    ):
        super().__init__(parent)
        self._user_id = user_id
        self._api_key = api_key
        self._on_auth_error = on_auth_error
        self._on_task_start = on_task_start
        self._on_task_end = on_task_end
        self._retry_delay_ms = _RETRY_BASE_MS
        self._pending_retry: Optional[str] = None  # after() id
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Danger.TButton", foreground="red")

        title = tk.Label(self, text="Focasa", font=("Helvetica", 22, "bold"))
        title.grid(row=0, column=0, pady=(40, 4))

        status = tk.Label(
            self,
            text="Device registered",
            font=("Helvetica", 13),
            fg="#2a9d2a",
        )
        status.grid(row=1, column=0, pady=(0, 20))

        id_frame = tk.Frame(self, bd=1, relief="solid", padx=12, pady=8)
        id_frame.grid(row=2, column=0, pady=(0, 32))

        tk.Label(id_frame, text="User ID", font=("Helvetica", 10), fg="#888888").pack()
        tk.Label(
            id_frame,
            text=self._user_id,
            font=("Helvetica Neue", 11, "bold"),
            fg="#222222",
        ).pack()

        self._task_frame = tk.Frame(self)
        self._task_frame.grid(row=3, column=0)
        self._task_frame.columnconfigure(0, weight=1)

        self._status_label = tk.Label(
            self, text="", font=("Helvetica", 10), fg="#888888", wraplength=300
        )
        self._status_label.grid(row=4, column=0, pady=(8, 0))

        active = storage.load_active_task()
        if active:
            self._show_active(active["name"])
        else:
            self._show_idle()

    def _show_idle(self):
        for w in self._task_frame.winfo_children():
            w.destroy()

        vcmd = (self.register(self._validate_length), "%P")

        self._name_var = tk.StringVar()
        entry = ttk.Entry(
            self._task_frame,
            textvariable=self._name_var,
            width=34,
            validate="key",
            validatecommand=vcmd,
        )
        entry.grid(row=0, column=0, ipady=6, pady=(0, 10))
        entry.focus()
        entry.bind("<Return>", lambda _: self._submit())

        self._start_btn = ttk.Button(
            self._task_frame, text="Start Task", command=self._submit
        )
        self._start_btn.grid(row=1, column=0)

    def _show_active(self, name: str):
        for w in self._task_frame.winfo_children():
            w.destroy()

        tk.Label(
            self._task_frame,
            text="Active task",
            font=("Helvetica", 10),
            fg="#888888",
        ).grid(row=0, column=0, pady=(0, 4))

        tk.Label(
            self._task_frame,
            text=name,
            font=("Helvetica", 13, "bold"),
            fg="#222222",
            wraplength=300,
        ).grid(row=1, column=0)

        self._end_btn = ttk.Button(
            self._task_frame,
            text="End Task",
            command=self._end_submit,
            style="Danger.TButton",
        )
        self._end_btn.grid(row=2, column=0, pady=(12, 0))

    def _validate_length(self, proposed: str) -> bool:
        return len(proposed) <= 100

    def _submit(self):
        name = self._name_var.get().strip()
        if not name:
            self._set_status("Please enter a task name.", "#cc0000")
            return

        self._set_status("")
        self._start_btn.config(state="disabled", text="Starting…")
        self._retry_delay_ms = _RETRY_BASE_MS

        task_id = str(uuid.uuid4())
        start = datetime.now(tz=timezone.utc)
        threading.Thread(
            target=self._do_start, args=(task_id, name, start), daemon=True
        ).start()

    def _do_start(self, task_id: str, name: str, start: datetime):
        try:
            client.start_task(
                api_key=self._api_key,
                task_id=task_id,
                user_id=self._user_id,
                name=name,
                start=start,
            )
            storage.save_active_task(task_id=task_id, name=name, start=start.isoformat())
            self.after(0, lambda: self._on_start_success(name))
        except Exception as exc:
            self.after(0, lambda e=exc: self._on_start_error(e, task_id, name, start))

    def _on_start_success(self, name: str):
        self._set_status("")
        self._on_task_start()
        self._show_active(name)

    def _end_submit(self):
        active = storage.load_active_task()
        if not active:
            return

        self._set_status("")
        self._end_btn.config(state="disabled", text="Ending…")
        self._retry_delay_ms = _RETRY_BASE_MS

        task_id = active["task_id"]
        end = datetime.now(tz=timezone.utc)
        threading.Thread(
            target=self._do_end, args=(task_id, end), daemon=True
        ).start()

    def _do_end(self, task_id: str, end: datetime):
        try:
            client.end_task(
                api_key=self._api_key,
                task_id=task_id,
                user_id=self._user_id,
                end=end,
            )
            storage.clear_active_task()
            self.after(0, self._on_end_success)
        except Exception as exc:
            self.after(0, lambda e=exc: self._on_end_error(e, task_id, end))

    def _on_end_success(self):
        self._set_status("")
        self._on_task_end()
        self._show_idle()

    def _on_end_error(self, exc: Exception, task_id: str, end: datetime):
        status_code = self._http_status(exc)

        if status_code in (401, 403, 404):
            self._on_auth_error("Session expired. Please re-enter your API key.")
            return

        self._set_status("Network may be down, retrying…", "#cc6600")

        delay = self._retry_delay_ms
        self._retry_delay_ms = min(self._retry_delay_ms * 2, _RETRY_MAX_MS)

        self._pending_retry = self.after(
            delay,
            lambda: threading.Thread(
                target=self._do_end, args=(task_id, end), daemon=True
            ).start(),
        )

    def _on_start_error(self, exc: Exception, task_id: str, name: str, start: datetime):
        status_code = self._http_status(exc)

        if status_code in (401, 403, 404):
            self._on_auth_error("Session expired. Please re-enter your API key.")
            return

        self._set_status("Network may be down, retrying…", "#cc6600")

        delay = self._retry_delay_ms
        self._retry_delay_ms = min(self._retry_delay_ms * 2, _RETRY_MAX_MS)

        self._pending_retry = self.after(
            delay,
            lambda: threading.Thread(
                target=self._do_start, args=(task_id, name, start), daemon=True
            ).start(),
        )

    def _http_status(self, exc: Exception) -> Optional[int]:
        import requests
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            return exc.response.status_code
        return None

    def _set_status(self, message: str, color: str = "#888888"):
        self._status_label.config(text=message, fg=color)
