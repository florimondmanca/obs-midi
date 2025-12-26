import functools
import tkinter as tk
from tkinter import ttk

import mido

from ..core.obs_actions import MIDITrigger
from .constants import WM_CLASS_NAME


class DebugModal(tk.Toplevel):
    def __init__(
        self, parent: tk.Widget, *, midi_input: str, triggers: list[MIDITrigger]
    ) -> None:
        super().__init__(parent, class_=WM_CLASS_NAME)
        self.title("OBS MIDI - Debug")

        triggers = sorted(triggers, key=lambda t: t.sort_key())

        # Keep reference to hold port open
        self._output = mido.open_output(midi_input)

        container = ttk.Frame(self, padding=20)

        trigger_list_title = ttk.Label(container, text="MIDI Triggers")
        trigger_list = ttk.Frame(container)

        for i, trigger in enumerate(triggers):
            trigger_button = ttk.Button(
                trigger_list,
                text="Send",
                command=functools.partial(self._send, trigger),
            )
            trigger_name = ttk.Label(trigger_list, text=str(trigger))
            trigger_text = ttk.Label(trigger_list, text=trigger.text)

            trigger_button.grid(row=i, column=0, sticky="we", pady=2)
            trigger_name.grid(row=i, column=1, sticky="w", pady=2, padx=10)
            trigger_text.grid(row=i, column=2, sticky="w", pady=2)

        trigger_list.grid_columnconfigure(2, weight=1)

        trigger_list_title.grid(row=0, column=0, sticky="nwe")
        trigger_list.grid(row=1, column=0, sticky="nswe", pady=5)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        container.grid(row=0, column=0, sticky="nswe")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _send(self, trigger: MIDITrigger) -> None:
        self._output.send(trigger.get_message())
