import tkinter as tk

import rtmidi


class DebugModal(tk.Toplevel):
    def __init__(self, parent: tk.Widget, midi_input: str) -> None:
        super().__init__(parent)
        self.title("OBS MIDI - Debug")

        midi_in = rtmidi.MidiIn()
        print(midi_in.get_ports())
