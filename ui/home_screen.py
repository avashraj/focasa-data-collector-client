import tkinter as tk
from tkinter import ttk


class HomeScreen(tk.Frame):
    def __init__(self, parent, user_id: str):
        super().__init__(parent)
        self._user_id = user_id
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

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

        placeholder = tk.Label(
            self,
            text="Task controls will appear here.",
            font=("Helvetica", 11),
            fg="#aaaaaa",
        )
        placeholder.grid(row=3, column=0)
