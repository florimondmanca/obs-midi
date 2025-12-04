import logging
import threading
from typing import Any

import websockets
import websockets.sync.client

from .app import App

logger = logging.getLogger(__name__)


class ObsEventsThread(threading.Thread):
    def __init__(
        self,
        *,
        app: App,
        start_event: threading.Event,
        close_event: threading.Event,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._app = app
        self.start_event = start_event
        self._close_event = close_event

    def run(
        self,
    ) -> None:
        self.start_event.wait()

        client = self._app.client

        try:
            logger.info("Started")

            for event in client.iter_events():
                if self._close_event.is_set():
                    break

                if event is None:
                    continue

                if client.is_request_response(event):
                    request_data = client.get_request_data(event["d"]["requestId"])
                    self._app.on_response(event, request_data)

            logger.info("Stopped")
        except websockets.exceptions.ConnectionClosed:
            logger.info("OBS WebSocket connection was closed, stopping...")
            self._close_event.set()
            return
        except Exception as exc:
            logger.error(exc)
            raise
