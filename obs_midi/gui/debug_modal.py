import tkinter as tk

import mido

from .constants import WM_CLASS_NAME


class DebugModal(tk.Toplevel):
    def __init__(self, parent: tk.Widget, midi_input: str) -> None:
        super().__init__(parent, class_=WM_CLASS_NAME)
        self.title("OBS MIDI - Debug")

        # Keep reference to hold port open
        self._output = mido.open_output(midi_input)
