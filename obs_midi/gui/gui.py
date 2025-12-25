import logging
import tkinter as tk
from tkinter import ttk

from .main_page import MainPage

logger = logging.getLogger("obs_midi.gui")


class GUI:
    def __init__(self, root: tk.Tk) -> None:
        container = ttk.Frame(root)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        main_page = MainPage(container, self)
        main_page.grid(row=0, column=0, sticky="nsew")

        root.title("OBS MIDI")
        root.protocol(
            # Override window close button
            "WM_DELETE_WINDOW",
            main_page.on_quit,
        )
        root.bind("<Control-q>", lambda *args: main_page.on_quit())

        self._root = root
        self._main_page = main_page

        logger.info("Ready")

    def focus_none(self) -> None:
        # Focusing the root has the effect of unfocusing all other widgets
        self._root.focus()

    def update(self) -> None:
        self._root.update()

    def destroy(self) -> None:
        self._root.destroy()
