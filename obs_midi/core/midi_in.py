import logging
import threading
import time
from typing import Any

import mido
from rtmidi.midiutil import open_midiinput

from .app import App

logger = logging.getLogger(__name__)


class MIDInputThread(threading.Thread):
    def __init__(
        self,
        *,
        port: str | None,
        app: App,
        ready_event: threading.Event,
        close_event: threading.Event,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._port = port
        self._app = app
        self._ready_event = ready_event
        self._close_event = close_event

    def run(
        self,
    ) -> None:
        logger.debug("Selected port: %s", self._port)

        try:
            midi_input, port_name = open_midiinput(
                self._port,
                use_virtual=False,
                client_name="python-obs-midi",
                port_name="Midi In",
            )

            # https://spotlightkid.github.io/python-rtmidi/rtmidi.html#rtmidi.MidiIn.set_callback
            @midi_input.set_callback
            def midi_callback(event: tuple, data: object = None) -> None:
                try:
                    msg_bytes, _ = event
                    msg: mido.Message = mido.parse(msg_bytes)
                    logger.debug("Incoming message: %s", msg)
                    self._app.on_midi_message(msg)
                except Exception as exc:
                    logger.error(exc)
                    raise

            with midi_input:
                logger.info("Listening for messages...")
                self._ready_event.set()

                try:
                    while not self._close_event.is_set():
                        time.sleep(0.2)
                    logger.info("Stopped")
                except KeyboardInterrupt:
                    pass

        except Exception as exc:
            logger.error(exc)
            self._ready_event.set()
            self._close_event.set()
            raise
