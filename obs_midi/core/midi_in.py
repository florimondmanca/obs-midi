import logging
import queue
import threading
import time
from typing import Any, Callable

import mido

from .midi import MIDInputOpener

logger = logging.getLogger(__name__)


class MIDInputThread(threading.Thread):
    def __init__(
        self,
        *,
        input_opener: MIDInputOpener,
        on_error: Callable[[Exception], None] = lambda exc: None,
        ready_event: threading.Event,
        close_event: threading.Event,
        error_bucket: queue.Queue[Exception],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._input_opener = input_opener
        self._ready_event = ready_event
        self._close_event = close_event
        self._error_bucket = error_bucket
        self._message_handlers: list[Callable[[mido.Message], None]] = []

    def add_message_handler(self, cb: Callable[[mido.Message], None]) -> None:
        self._message_handlers.append(cb)

    def run(
        self,
    ) -> None:
        def midi_callback(msg: mido.Message) -> None:
            logger.debug("Incoming message: %s", msg)
            for handle_message in self._message_handlers:
                handle_message(msg)

        try:
            with self._input_opener(midi_callback):
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
            self._error_bucket.put_nowait(exc)
