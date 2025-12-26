import logging
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

import mido

if TYPE_CHECKING:
    from .gui import GUI

logger = logging.getLogger("obs_midi.gui")


class ConfigForm(ttk.Frame):
    _MIDI_PORT_VIRTUAL = "<New virtual MIDI port>"

    def __init__(self, parent: tk.Widget, gui: "GUI") -> None:
        super().__init__(parent)
        self._gui = gui

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
        self._midi_port_entry.bind("<Return>", lambda *args: self._submit())
        self._add_field(row=0, label_text="midi-port", widget=self._midi_port_entry)

        # OBS Port
        self._obs_port = tk.IntVar(value=4455)
        self._obs_port.trace_add("write", lambda *args: self._update())
        self._obs_port_entry = ttk.Entry(
            self,
            textvariable=self._obs_port,
            width=width,
        )
        self._obs_port_entry.bind("<Return>", lambda *args: self._submit())
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
        self._obs_password_entry.bind("<Return>", lambda *args: self._submit())
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

    def _submit(self) -> None:
        if self._can_run():
            self._gui.focus_none()
            self._on_click_cta()

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
        self._set_disabled(True)
        self._cta_button.config(state=tk.DISABLED)
        self._status_label.config(foreground="grey")

    def _set_running(self) -> None:
        self._cta_button.config(state=tk.NORMAL)
        self._cta_label.set("Stop")
        self._status.set("Running")
        self._status_label.config(foreground="green")

    def _set_disconnected(self) -> None:
        self._status.set("OBS disconnected. Reconnecting...")
        self._status_label.config(foreground="darkorange")

    def _set_error(self, exc: Exception) -> None:
        self._set_disabled(False)
        self._cta_label.set("Start")
        self._cta_button.config(state=tk.NORMAL)
        self._status.set(f"Error: {exc}" if str(exc) else "Error")
        self._status_label.config(foreground="red")

    def _set_stopped(self) -> None:
        self._set_disabled(False)
        self._cta_label.set("Start")
        self._status.set("")
        self._status_label.config(foreground="grey")

    def _on_click_cta(self) -> None:
        if self._gui.is_application_running():
            self._gui.stop_application()
            return

        self._set_starting()

        self._gui.start_application(
            midi_port=(
                None
                if (midi_port := self._midi_port.get()) == self._MIDI_PORT_VIRTUAL
                else midi_port
            ),
            obs_port=int(self._obs_port.get()),
            obs_password=self._obs_password.get(),
            on_ready=lambda: self._set_running(),
            on_obs_disconnect=lambda: self._set_disconnected(),
            on_obs_reconnect=lambda: self._set_running(),
            on_error=lambda exc: self._set_error(exc),
            on_stopped=lambda: self._set_stopped(),
        )
