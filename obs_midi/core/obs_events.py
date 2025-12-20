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
        start_event: threading.Event,
        close_event: threading.Event,
        error_bucket: queue.Queue[Exception],
        on_disconnect: Callable[[], None],
        on_reconnect: Callable[[], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._client = client
        self._start_event = start_event
        self._close_event = close_event
        self._error_bucket = error_bucket
        self._on_disconnect = on_disconnect
        self._on_reconnect = on_reconnect
        self._reconnect_delay = 1
        self._event_handlers: list[Callable[[dict], None]] = []

    def add_event_handler(self, cb: Callable[[dict], None]) -> None:
        self._event_handlers.append(cb)

    def _reconnect(self) -> None:
        while True:
            logger.warn(
                "Reconnecting in %s seconds...",
                self._reconnect_delay,
            )

            time.sleep(self._reconnect_delay)

            if self._close_event.is_set():
                break

            try:
                self._client.reconnect()
            except ConnectionError:
                continue
            else:
                break

    def run(
        self,
    ) -> None:
        self._start_event.wait()

        while True:
            try:
                logger.info("Started")

                for event in self._client.iter_events():
                    if self._close_event.is_set():
                        return

                    if event is None:
                        continue

                    for handle_event in self._event_handlers:
                        handle_event(event)

                logger.info("Stopped")
                break
            except ObsDisconnect:
                logger.warn("OBS disconnected.")
                self._on_disconnect()
                self._reconnect()
                self._on_reconnect()
                continue
            except Exception as exc:
                logger.error(exc)
                self._close_event.set()
                self._error_bucket.put_nowait(exc)
                raise
