import logging
import threading
from typing import Any, Callable

import websockets
import websockets.sync.client

from .obs_client import ObsClient

logger = logging.getLogger(__name__)


class ObsEventsThread(threading.Thread):
    def __init__(
        self,
        *,
        client: ObsClient,
        start_event: threading.Event,
        close_event: threading.Event,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._client = client
        self._start_event = start_event
        self._close_event = close_event
        self._event_handlers: list[Callable[[dict], None]] = []

    def add_event_handler(self, cb: Callable[[dict], None]) -> None:
        self._event_handlers.append(cb)

    def run(
        self,
    ) -> None:
        self._start_event.wait()

        try:
            logger.info("Started")

            for event in self._client.iter_events():
                if self._close_event.is_set():
                    break

                if event is None:
                    continue

                for handle_event in self._event_handlers:
                    handle_event(event)

            logger.info("Stopped")
        except websockets.exceptions.ConnectionClosed:
            logger.info("OBS WebSocket connection was closed, stopping...")
            self._close_event.set()
            return
        except Exception as exc:
            logger.error(exc)
            raise
