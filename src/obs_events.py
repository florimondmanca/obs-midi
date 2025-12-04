import threading

import websockets
import websockets.sync.client

from .app import App


class ObsEventsThread(threading.Thread):
    def __init__(
        self,
        *,
        app: App,
        start_event: threading.Event,
        close_event: threading.Event,
    ) -> None:
        super().__init__()
        self._app = app
        self.start_event = start_event
        self._close_event = close_event

    def run(
        self,
    ) -> None:
        def log(*values: object) -> None:
            print("[obs][events]", *values)

        self.start_event.wait()

        client = self._app.client

        try:
            log("Started")

            for event in client.iter_events():
                if self._close_event.is_set():
                    break

                if event is None:
                    continue

                if client.is_request_response(event):
                    request_data = client.get_request_data(event["d"]["requestId"])
                    self._app.on_response(event, request_data)

            log("Stopped")
        except websockets.exceptions.ConnectionClosed:
            log("INFO: OBS WebSocket connection was closed, stopping...")
            self._close_event.set()
            return
        except Exception as exc:
            log("ERROR:", exc)
            raise
