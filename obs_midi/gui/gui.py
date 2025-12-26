import logging
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..core.main import INFO_MIDI_INPUT_PORT_NAME, INFO_MIDI_TRIGGERS, run
from ..core.midi_in import mido_input_opener
from .config_form import ConfigForm
from .debug_modal import DebugModal
from .menu import Menu

logger = logging.getLogger("obs_midi.gui")


class GUI:
    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._application_thread: threading.Thread | None = None
        self._application_info: dict | None = None
        self._debug_modal: DebugModal | None = None
        self._close_event = threading.Event()

        root.title("OBS MIDI")

        self._menu = Menu(root, self)

        container = ttk.Frame(root)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        main_page = ttk.Frame(container, padding=30)
        main_page.grid(row=0, column=0, sticky="nsew")

        config_form = ConfigForm(main_page, self)
        config_form.grid(row=0, column=0, sticky="n")
        main_page.grid_rowconfigure(0, weight=1)

        root.protocol("WM_DELETE_WINDOW", self.destroy)  # Window close button
        root.bind("<Control-q>", lambda *args: self.destroy())

        logger.info("Ready")

    def open_midi_debug_modal(self) -> None:
        if self._debug_modal is not None:
            self._debug_modal.focus()
            # Place on top
            # https://stackoverflow.com/a/45064895
            self._debug_modal.attributes("-topmost", True)
            self._debug_modal.update()
            self._debug_modal.attributes("-topmost", False)
            return

        assert self._application_info is not None

        self._debug_modal = DebugModal(
            self._root,
            midi_input=self._application_info[INFO_MIDI_INPUT_PORT_NAME],
            triggers=self._application_info[INFO_MIDI_TRIGGERS],
        )

        def on_debug_modal_closed() -> None:
            assert self._debug_modal is not None
            self._debug_modal.destroy()
            self._debug_modal = None

        self._debug_modal.protocol("WM_DELETE_WINDOW", lambda: on_debug_modal_closed())

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
        self._application_info = None

        self._close_event.clear()

        def _run() -> None:
            logger.info("Application thread has started")

            def _on_ready(info: dict) -> None:
                on_ready()
                self._application_info = info
                self._menu.set_open_midi_debug_modal_state(tk.NORMAL)

            try:
                run(
                    midi_input_opener=mido_input_opener(port=midi_port),
                    obs_port=obs_port,
                    obs_password=obs_password,
                    on_ready=_on_ready,
                    on_obs_disconnect=on_obs_disconnect,
                    on_obs_reconnect=on_obs_reconnect,
                    close_event=self._close_event,
                )
            except Exception as exc:
                logger.exception("Application returned an error: %s", repr(exc))
                on_error(exc)
            else:
                logger.info("Application has stopped")
                on_stopped()

        logger.info("Starting application thread")
        t = threading.Thread(target=_run)
        t.daemon = True
        t.start()
        self._application_thread = t

    def is_application_running(self) -> bool:
        return (
            self._application_thread is not None and self._application_thread.is_alive()
        )

    def stop_application(self) -> None:
        self._close_event.set()
        self._menu.set_open_midi_debug_modal_state(tk.DISABLED)

        # Be careful not to block the main GUI thread
        while (
            self._application_thread is not None and self._application_thread.is_alive()
        ):
            self._application_thread.join(0.1)
            self._root.update()

        self._application_thread = None

    def focus_none(self) -> None:
        # Focusing the root has the effect of unfocusing all other widgets
        self._root.focus()

    def destroy(self) -> None:
        self.stop_application()
        self._root.destroy()
