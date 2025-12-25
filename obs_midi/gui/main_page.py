import logging
import threading
from tkinter import ttk
from typing import TYPE_CHECKING, Callable

from ..core.main import run
from ..core.midi_in import mido_input_opener
from .config_form import ConfigForm
from .debug_modal import DebugModal

if TYPE_CHECKING:
    from .gui import GUI

logger = logging.getLogger("obs_midi.gui")


class MainPage(ttk.Frame):
    def __init__(self, parent: ttk.Frame, gui: "GUI") -> None:
        super().__init__(parent, padding=30)

        self._gui = gui
        self._application_thread: threading.Thread | None = None
        self._close_event = threading.Event()

        config_form = ConfigForm(self, gui)
        debug_button = ttk.Button(
            self,
            text="Open debug modal",
            command=lambda: DebugModal(self, midi_input=config_form.get_midi_input()),
        )

        config_form.grid(row=0, column=0, sticky="n")
        debug_button.grid(row=1, column=0, sticky="n")
        self.grid_rowconfigure(0, weight=1)

    def on_quit(self) -> None:
        self.stop_application()
        self._gui.destroy()

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
                    midi_input_opener=mido_input_opener(port=midi_port),
                    obs_port=obs_port,
                    obs_password=obs_password,
                    on_ready=on_ready,
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

        # Be careful not to block the main GUI thread
        while (
            self._application_thread is not None and self._application_thread.is_alive()
        ):
            self._application_thread.join(0.1)
            self._gui.update()

        self._application_thread = None
