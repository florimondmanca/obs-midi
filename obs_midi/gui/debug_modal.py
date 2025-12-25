import tkinter as tk

import mido


class DebugModal(tk.Toplevel):
    def __init__(self, parent: tk.Widget, midi_input: str) -> None:
        super().__init__(parent)
        self.title("OBS MIDI - Debug")

        print(mido.get_output_names())
