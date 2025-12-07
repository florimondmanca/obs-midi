import logging
import threading
import tkinter as tk
from tkinter import ttk

import mido
from ttkthemes import ThemedTk

from .core.main import run
from .logging import LOGGING_CONFIG

INPUT_WIDTH = 35
FIELD_PADY = 5


def run_gui() -> None:
    root = ThemedTk(
        theme="yaru",
        # This should match the StartupWMClass in 'obs-midi.desktop' so that
        # under Linux, X server knows to group the tkinter window with the launcher icon.
        className="obs-midi",
    )
    root.title("python-obs-midi")
    MainApplication(root)
    root.mainloop()


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


class MainPage(ttk.Frame):
    def __init__(self, parent: ttk.Frame, app: MainApplication) -> None:
        super().__init__(parent)

        self._thread: threading.Thread | None = None
        self._close_event = threading.Event()

        header = ttk.Frame(self, padding=(0, 10))
        ttk.Label(header, text="OBS MIDI", justify="center").pack(expand=True)

        config = ttk.Frame(self, padding=(10, 10), borderwidth=1, border=10)

        available_midi_ports = mido.get_input_names()

        self._midi_port = tk.StringVar(
            value=available_midi_ports[0] if available_midi_ports else ""
        )
        self._midi_port.trace_add("write", lambda *args: self._update())
        ttk.Label(config, text="midi-port", justify="left").grid(
            row=0, column=0, padx=(0, 10), pady=FIELD_PADY, sticky="w"
        )
        self._midi_port_entry = ttk.Combobox(
            config,
            textvariable=self._midi_port,
            values=available_midi_ports,
        )
        self._midi_port_entry.grid(row=0, column=1, pady=FIELD_PADY, sticky="we")

        self._obs_port = tk.IntVar(value=4455)
        self._obs_port.trace_add("write", lambda *args: self._update())
        ttk.Label(config, text="obs-port", justify="left").grid(
            row=1, column=0, padx=(0, 10), pady=FIELD_PADY, sticky="w"
        )
        self._obs_port_entry = ttk.Entry(
            config, width=INPUT_WIDTH, textvariable=self._obs_port
        )
        self._obs_port_entry.grid(row=1, column=1, pady=FIELD_PADY)

        self._obs_password = tk.StringVar()
        self._obs_password.trace_add("write", lambda *args: self._update())
        ttk.Label(config, text="obs-password", justify="left").grid(
            row=2, column=0, padx=(0, 10), pady=FIELD_PADY, sticky="w"
        )
        self._obs_password_entry = ttk.Entry(
            config, width=INPUT_WIDTH, show="*", textvariable=self._obs_password
        )
        self._obs_password_entry.grid(row=2, column=1, pady=FIELD_PADY)

        self._config_widgets = [
            self._midi_port_entry,
            self._obs_port_entry,
            self._obs_password_entry,
        ]

        self._cta_label = tk.StringVar(value="Start")
        self._cta_button = ttk.Button(
            config,
            textvariable=self._cta_label,
            state=tk.DISABLED,
            command=self._on_click_cta,
        )
        self._cta_button.grid(row=3, column=0, columnspan=2)
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

    def _update(self) -> None:
        self._cta_button.config(state=tk.NORMAL if self._can_run() else tk.DISABLED)

    def _can_run(self) -> bool:
        try:
            self._obs_port.get()
        except tk.TclError:
            return False

        return bool(self._midi_port.get()) and bool(self._obs_password.get())

    def _set_starting(self) -> None:
        self._cta_label.set("Stop")
        for widget in self._config_widgets:
            widget.config(state=tk.DISABLED)

    def _set_running(self) -> None:
        self._status.set("Running")
        self._status_label.config(foreground="green")

    def _set_error(self) -> None:
        self._status.set("Error")
        self._status_label.config(foreground="red")

    def _set_stopped(self) -> None:
        self._close_event.set()
        # Don't join() to avoid blocking GUI mainloop
        # Be confident the thread will terminate soon
        self._thread = None

        self._cta_label.set("Start")
        self._status.set("")
        self._status_label.config(foreground="black")
        for widget in self._config_widgets:
            widget.config(state=tk.NORMAL)

    def _run_in_thread(self) -> None:
        try:
            self._set_starting()
            run(
                midi_port=self._midi_port.get(),
                obs_port=int(self._obs_port.get()),
                obs_password=self._obs_password.get(),
                on_ready=lambda: self._set_running(),
                close_event=self._close_event,
            )
        except Exception:
            self._set_error()
        else:
            # NOTE: we may reach this point if OBS closes the connection on their end,
            # e.g. if OBS was closed.
            self._set_stopped()

    def _on_click_cta(self) -> None:
        if self._thread is not None:
            self._set_stopped()
            return

        self._close_event.clear()
        t = threading.Thread(target=self._run_in_thread)
        t.daemon = True
        t.start()
        self._thread = t


if __name__ == "__main__":
    logging.config.dictConfig(LOGGING_CONFIG)
    run_gui()
