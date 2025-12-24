import contextlib
import logging
import queue
import threading
from typing import Any, Callable, ContextManager, Iterator

import mido
from rtmidi.midiutil import open_midiinput

logger = logging.getLogger(__name__)


MIDICallback = Callable[[mido.Message], None]
MIDInputOpener = Callable[[MIDICallback], ContextManager[None]]


def rtmidi_input_opener(*, port: str | None) -> MIDInputOpener:
    @contextlib.contextmanager
    def _open_rtmidi_input(callback: MIDICallback) -> Iterator[None]:
        logger.debug("Selected port: %s", port)

        midi_input, port_name = open_midiinput(
            port,
            use_virtual=True,
            client_name="OBS MIDI",
            port_name="Midi In",
            interactive=False,
        )

        # https://spotlightkid.github.io/python-rtmidi/rtmidi.html#rtmidi.MidiIn.set_callback
        @midi_input.set_callback
        def midi_callback(event: tuple, data: object = None) -> None:
            try:
                msg_bytes, _ = event
                msg: mido.Message = mido.parse(msg_bytes)
                callback(msg)
            except Exception as exc:
                logger.error(exc)
                raise

        with midi_input:
            yield

    return _open_rtmidi_input


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
                logger.info("MIDI input is open")

                try:
                    self._start_barrier.wait()
                except threading.BrokenBarrierError:
                    logger.error("Aborting...")
                    return

                logger.info("Listening for messages...")

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
