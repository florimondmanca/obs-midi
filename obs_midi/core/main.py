import logging
import logging.config
import queue
import threading
import time
from typing import Callable

from .app import App
from .midi_in import MIDInputThread
from .obs_client import open_obs_client
from .obs_events import ObsEventsThread

logger = logging.getLogger(__name__)


def run(
    midi_port: str | None,
    obs_port: int,
    obs_password: str,
    *,
    interactive: bool,
    on_ready: Callable[[], None] = lambda: None,
    close_event: threading.Event | None = None,
) -> None:
    midi_ready_event = threading.Event()

    if close_event is None:
        close_event = threading.Event()

    error_bucket: queue.Queue[Exception] = queue.Queue()

    with open_obs_client(port=obs_port, password=obs_password) as client:
        app = App(client=client, on_ready=on_ready)

        midi_input_thread = MIDInputThread(
            app=app,
            port=midi_port,
            interactive=interactive,
            ready_event=midi_ready_event,
            close_event=close_event,
            error_bucket=error_bucket,
            daemon=True,
        )

        obs_events_thread = ObsEventsThread(
            app=app,
            start_event=midi_ready_event,
            close_event=close_event,
            daemon=True,
        )

        threads = [
            midi_input_thread,
            obs_events_thread,
        ]

        for thread in threads:
            thread.start()

        def close_all_threads() -> None:
            close_event.set()
            for thread in threads:
                thread.join()

        midi_ready_event.wait()
        app.send_initial_request()

        try:
            while all(t.is_alive() for t in threads):
                time.sleep(0.2)

                if close_event.is_set():
                    break

            try:
                exc = error_bucket.get_nowait()
            except queue.Empty:
                pass
            else:
                raise exc
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            close_all_threads()
