import argparse
import logging
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

import mido
from ttkthemes import ThemedTk

from .core.main import run
from .core.midi import rtmidi_input_opener
from .logging import LOGGING_CONFIG

logger = logging.getLogger(__name__)


def run_gui() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)

    root = ThemedTk(
        # This should match the StartupWMClass in 'obs-midi.desktop' so that
        # under Linux, X server knows to group the tkinter window with the launcher icon.
        className="obs-midi",
    )

    parser = argparse.ArgumentParser(prog="obs-midi")
    parser.set_defaults(theme="yaru")
    args = parser.parse_args()

    root.set_theme(args.theme)
    root.title("OBS MIDI")

    MainApplication(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass


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
        super().__init__(parent, padding=30)

        self._thread: threading.Thread | None = None
        self._close_event = threading.Event()

        config_form = ConfigForm(self)

        footer = ttk.Frame(self, padding=(0, 30, 0, 0))
        ttk.Button(footer, text="Quit", command=app.quit).pack()

        config_form.grid(row=0, column=0, sticky="n")
        footer.grid(row=1, column=0, sticky="we")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def start_application(
        self,
        *,
        midi_port: str | None,
        obs_port: int,
        obs_password: str,
        on_ready: Callable[[], None] = lambda: None,
        on_obs_disconnect: Callable[[], None] = lambda: None,
        on_obs_reconnect: Callable[[], None] = lambda: None,
        on_error: Callable[[Exception], None] = lambda exc: None,
        on_stopped: Callable[[], None] = lambda: None,
    ) -> None:
        assert not self.is_application_running(), "Application is already running"

        self._close_event.clear()

        def _run() -> None:
            logger.info("Application thread has started")

            try:
                run(
                    midi_input_opener=rtmidi_input_opener(
                        port=midi_port, interactive=False
                    ),
                    obs_port=obs_port,
                    obs_password=obs_password,
                    on_ready=on_ready,
                    on_obs_disconnect=on_obs_disconnect,
                    on_obs_reconnect=on_obs_reconnect,
                    close_event=self._close_event,
                )
            except Exception as exc:
                logger.error("Application returned an error: %s", repr(exc))
                on_error(exc)
            else:
                # NOTE: we may reach this point if OBS closes the connection on their end,
                # e.g. if OBS was closed.
                logger.info("Application has stopped")
                on_stopped()

        logger.info("Starting application thread")
        t = threading.Thread(target=_run)
        t.daemon = True
        t.start()
        self._thread = t

    def is_application_running(self) -> bool:
        return self._thread is not None

    def stop_application(self) -> None:
        assert self.is_application_running(), "Application is not running"
        self._close_event.set()
        # Don't join() to avoid blocking GUI mainloop
        # Be confident the thread will terminate soon
        self._thread = None


class ConfigForm(ttk.Frame):
    _MIDI_PORT_VIRTUAL = "<New virtual MIDI port>"

    def __init__(self, main_page: MainPage) -> None:
        super().__init__(main_page)
        self._main_page = main_page

        available_midi_ports = mido.get_input_names()
        midi_port_options = [self._MIDI_PORT_VIRTUAL, *available_midi_ports]
        width = max((len(p) for p in midi_port_options))

        # MIDI Input Port
        self._midi_port = tk.StringVar(value=midi_port_options[0])
        self._midi_port.trace_add("write", lambda *args: self._update())
        self._midi_port_entry = ttk.Combobox(
            self,
            textvariable=self._midi_port,
            values=midi_port_options,
        )
        self._add_field(row=0, label_text="midi-port", widget=self._midi_port_entry)

        # OBS Port
        self._obs_port = tk.IntVar(value=4455)
        self._obs_port.trace_add("write", lambda *args: self._update())
        self._obs_port_entry = ttk.Entry(
            self,
            textvariable=self._obs_port,
            width=width,
        )
        self._add_field(row=1, label_text="obs-port", widget=self._obs_port_entry)

        # OBS Password
        self._obs_password = tk.StringVar()
        self._obs_password.trace_add("write", lambda *args: self._update())
        self._obs_password_entry = ttk.Entry(
            self,
            show="*",
            textvariable=self._obs_password,
            width=width,
        )
        self._add_field(
            row=2, label_text="obs-password", widget=self._obs_password_entry
        )

        self._field_widgets = [
            self._midi_port_entry,
            self._obs_port_entry,
            self._obs_password_entry,
        ]

        cta_frame = ttk.Frame(self, padding=10)

        self._cta_label = tk.StringVar(value="Start")
        self._cta_button = ttk.Button(
            cta_frame,
            textvariable=self._cta_label,
            state=tk.DISABLED,
            command=self._on_click_cta,
        )
        self._cta_button.grid(row=0, column=0)
        self._status = tk.StringVar()
        self._status_label = ttk.Label(cta_frame, textvariable=self._status)
        self._status_label.grid(row=1, column=0)

        cta_frame.grid(row=3, column=0, columnspan=2)

        self.grid_columnconfigure(1, weight=1)

    def _add_field(self, row: int, label_text: str, widget: ttk.Widget) -> None:
        ttk.Label(self, text=label_text, justify="left").grid(
            row=row, column=0, padx=(0, 10), pady=5, sticky="w"
        )
        widget.grid(row=row, column=1, pady=5, sticky="we")

    def _update(self) -> None:
        self._cta_button.config(state=tk.NORMAL if self._can_run() else tk.DISABLED)

    def _can_run(self) -> bool:
        try:
            self._obs_port.get()
        except tk.TclError:
            return False

        return bool(self._midi_port.get() and self._obs_password.get())

    def _set_disabled(self, disabled: bool) -> None:
        for widget in self._field_widgets:
            widget.config(state=tk.DISABLED if disabled else tk.NORMAL)

    def _set_starting(self) -> None:
        self._cta_label.set("Stop")
        self._set_disabled(True)

    def _set_running(self) -> None:
        self._status.set("Running")
        self._status_label.config(foreground="green")

    def _set_disconnected(self) -> None:
        self._status.set("OBS disconnected. Reconnecting...")
        self._status_label.config(foreground="darkorange")

    def _set_error(self, exc: Exception) -> None:
        self._status.set("Error")
        self._status_label.config(foreground="red")

    def _set_stopped(self) -> None:
        self._main_page.stop_application()
        self._cta_label.set("Start")
        self._status.set("")
        self._status_label.config(foreground="black")
        self._set_disabled(False)

    def _on_click_cta(self) -> None:
        if self._main_page.is_application_running():
            self._set_stopped()
            return

        self._set_starting()

        midi_port = self._midi_port.get()

        self._main_page.start_application(
            midi_port=midi_port if midi_port != self._MIDI_PORT_VIRTUAL else None,
            obs_port=int(self._obs_port.get()),
            obs_password=self._obs_password.get(),
            on_ready=lambda: self._set_running(),
            on_obs_disconnect=lambda: self._set_disconnected(),
            on_obs_reconnect=lambda: self._set_running(),
            on_error=lambda exc: self._set_error(exc),
            on_stopped=lambda: self._set_stopped(),
        )


if __name__ == "__main__":
    run_gui()
