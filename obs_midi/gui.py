import threading
import tkinter as tk
from tkinter import ttk

import mido
from ttkthemes import ThemedTk

from .core.main import run

INPUT_WIDTH = 30
FIELD_PADY = 5


def run_gui() -> None:
    root = ThemedTk(theme="yaru")
    root.title("python-obs-midi")
    MainApplication(root)
    root.mainloop()


class MainPage(ttk.Frame):
    def __init__(self, parent: ttk.Frame, app: "MainApplication") -> None:
        super().__init__(parent)

        self._thread: threading.Thread | None = None
        self._close_event = threading.Event()

        header = ttk.Frame(self, padding=(0, 10))
        ttk.Label(header, text="OBS MIDI", justify="center").pack(expand=True)

        config = ttk.Frame(self, padding=(10, 10), borderwidth=1, border=10)

        self._midi_port = tk.StringVar()
        ttk.Label(config, text="midi-port", justify="left").grid(
            row=0, column=0, padx=(0, 10), pady=FIELD_PADY, sticky="w"
        )
        ttk.Combobox(
            config,
            width=INPUT_WIDTH,
            textvariable=self._midi_port,
            values=mido.get_input_names(),
        ).grid(row=0, column=1, pady=FIELD_PADY)

        self._obs_port = tk.IntVar(value=4455)
        ttk.Label(config, text="obs-port", justify="left").grid(
            row=1, column=0, padx=(0, 10), pady=FIELD_PADY, sticky="w"
        )
        ttk.Entry(config, width=INPUT_WIDTH, textvariable=self._obs_port).grid(
            row=1, column=1, pady=FIELD_PADY
        )

        self._obs_password = tk.StringVar()
        ttk.Label(config, text="obs-password", justify="left").grid(
            row=2, column=0, padx=(0, 10), pady=FIELD_PADY, sticky="w"
        )
        ttk.Entry(
            config, width=INPUT_WIDTH, show="*", textvariable=self._obs_password
        ).grid(row=2, column=1, pady=FIELD_PADY)

        self._cta_label = tk.StringVar(value="Start")
        ttk.Button(
            config, textvariable=self._cta_label, command=self._on_click_cta
        ).grid(row=3, column=0, columnspan=2)
        self._status = tk.StringVar()
        self._status_label = ttk.Label(config, textvariable=self._status)
        self._status_label.grid(row=4, column=0, columnspan=2)

        footer = ttk.Frame(self, padding=(0, 10))
        ttk.Button(footer, text="Quit", command=app.quit).pack()

        header.grid(row=0, column=0, sticky="we")
        config.grid(row=1, column=0, sticky="n")
        footer.grid(row=2, column=0, sticky="we")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _run_in_thread(self) -> None:
        try:
            self._status.set("Running")
            self._status_label.config(foreground="green")
            run(
                midi_port=self._midi_port.get(),
                obs_port=self._obs_port.get(),
                obs_password=self._obs_password.get(),
                close_event=self._close_event,
            )
        except Exception:
            self._status.set("Error")
            self._status_label.config(foreground="red")
        else:
            self._status.set("")
            self._status_label.config(foreground="black")

    def _on_click_cta(self) -> None:
        if self._thread is not None:
            self._close_event.set()
            # Don't join() to avoid blocking GUI mainloop
            # Be confident the thread will terminate soon
            self._thread = None
            self._cta_label.set("Start")
            return

        self._close_event.clear()
        t = threading.Thread(target=self._run_in_thread)
        t.daemon = True
        t.start()
        self._thread = t
        self._cta_label.set("Stop")


class MainApplication:
    def __init__(self, root: tk.Tk) -> None:
        container = ttk.Frame(root)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        main_page = MainPage(container, self)
        main_page.grid(row=0, column=0, sticky="nsew")

        self._root = root

    def quit(self) -> None:
        self._root.destroy()
