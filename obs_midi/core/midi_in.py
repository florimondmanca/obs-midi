import logging
import queue
import threading
from typing import Any, Callable

import mido

from .midi import MIDInputOpener

logger = logging.getLogger(__name__)


class MIDInputThread(threading.Thread):
    def __init__(
        self,
        *,
        input_opener: MIDInputOpener,
        start_barrier: threading.Barrier,
        close_event: threading.Event,
        error_bucket: queue.Queue[Exception],
        on_error: Callable[[Exception], None] = lambda exc: None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._input_opener = input_opener
        self._start_barrier = start_barrier
        self._close_event = close_event
        self._error_bucket = error_bucket
        self._message_handlers: list[Callable[[mido.Message], None]] = []

    def add_message_handler(self, cb: Callable[[mido.Message], None]) -> None:
        self._message_handlers.append(cb)

    def run(
        self,
    ) -> None:
        def midi_callback(msg: mido.Message) -> None:
            logger.info("Incoming MIDI message: %s", msg)

            for handler in self._message_handlers:
                handler(msg)

        try:
            with self._input_opener(midi_callback):
                logger.info("MIDI input is open, listening for messages...")

                try:
                    self._start_barrier.wait()
                except threading.BrokenBarrierError:
                    logger.error("Aborting...")
                    return

                try:
                    self._close_event.wait()
                    logger.info("Stopping...")
                except KeyboardInterrupt:
                    pass
        except Exception as exc:
            logger.error(exc)
            self._start_barrier.abort()
            self._close_event.set()
            self._error_bucket.put_nowait(exc)
        finally:
            logger.info("Stopped")
