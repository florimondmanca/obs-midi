import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gui import GUI


class Menu:
    def __init__(self, root: tk.Tk, gui: "GUI") -> None:
        menu = tk.Menu()
        root.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Quit",
            command=lambda: gui.destroy(),
            accelerator="Ctrl+Q",
            underline=0,
        )

        tools_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(
            label="Open MIDI debug window",
            command=lambda: gui.open_midi_debug_modal(),
            state=tk.DISABLED,
            underline=5,
        )
        self._tools_menu = tools_menu

    def set_open_midi_debug_modal_state(self, state: str) -> None:
        self._tools_menu.entryconfig("Open MIDI debug window", state=state)
