import logging
import queue
import threading
import time
from typing import Any, Callable

from .obs_client import ObsClient, ObsDisconnect

logger = logging.getLogger(__name__)


class ObsEventsThread(threading.Thread):
    def __init__(
        self,
        *,
        client: ObsClient,
        start_barrier: threading.Barrier,
        close_event: threading.Event,
        error_bucket: queue.Queue[Exception],
        on_disconnect: Callable[[], None],
        on_reconnect: Callable[[], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._client = client
        self._start_barrier = start_barrier
        self._close_event = close_event
        self._error_bucket = error_bucket
        self._on_disconnect = on_disconnect
        self._on_reconnect = on_reconnect
        self._reconnect_delay = 2
        self._event_handlers: list[Callable[[dict], None]] = []

    def add_event_handler(self, cb: Callable[[dict], None]) -> None:
        self._event_handlers.append(cb)

    def _reconnect(self) -> None:
        while True:
            logger.warning(
                "Attempting new connection in %d seconds...",
                self._reconnect_delay,
            )

            time.sleep(self._reconnect_delay)

            if self._close_event.is_set():
                break

            try:
                self._client.reconnect()
            except ConnectionError:
                logger.error("Reconnection failed")
                continue
            else:
                logger.info("Reconnection successful")
                break

    def run(
        self,
    ) -> None:
        try:
            self._client.connect()
            logger.info("Connected to OBS WebSocket")

            try:
                self._start_barrier.wait()
            except threading.BrokenBarrierError:
                logger.error("Aborting...")
                return

            while True:
                logger.info("Listening for WebSocket messages...")

                try:
                    for event in self._client.iter_events(poll_interval=0.2):
                        if self._close_event.is_set():
                            logger.info("Stopping...")
                            break

                        if event is None:
                            continue

                        for handle_event in self._event_handlers:
                            handle_event(event)

                    break
                except ObsDisconnect:
                    logger.warning("OBS WebSocket disconnected")
                    self._on_disconnect()

                    self._reconnect()

                    if self._close_event.is_set():
                        logger.info("Stopping...")
                        break

                    self._on_reconnect()
        except Exception as exc:
            logger.exception(exc)
            self._start_barrier.abort()
            self._close_event.set()
            self._error_bucket.put_nowait(exc)
        finally:
            logger.info("Stopped")
