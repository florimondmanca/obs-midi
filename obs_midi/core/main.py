import logging
import logging.config
import queue
import threading
from typing import Callable

from .midi_in import MIDInputOpener, MIDInputThread
from .obs_actions import ObsActions
from .obs_client import ObsClient
from .obs_events import ObsEventsThread
from .obs_init import ObsInitThread

logger = logging.getLogger(__name__)

INFO_MIDI_INPUT_PORT_NAME = "midi_input_port_name"


def run(
    midi_input_opener: MIDInputOpener,
    obs_port: int,
    obs_password: str,
    *,
    on_ready: Callable[[dict], None] = lambda info: None,
    on_obs_disconnect: Callable[[], None] = lambda: None,
    on_obs_reconnect: Callable[[], None] = lambda: None,
    obs_reconnect_delay: float = 2,
    close_event: threading.Event | None = None,
) -> None:
    if close_event is None:
        close_event = threading.Event()

    error_bucket: queue.Queue[Exception] = queue.Queue()
    client = ObsClient(port=obs_port, password=obs_password)
    obs_actions = ObsActions()
    start_barrier = threading.Barrier(3)

    midi_input_thread = MIDInputThread(
        input_opener=midi_input_opener,
        start_barrier=start_barrier,
        close_event=close_event,
        error_bucket=error_bucket,
        daemon=True,
    )
    midi_input_thread.add_message_handler(
        lambda msg: obs_actions.process(msg, client=client)
    )

    ws_open_event = threading.Event()

    obs_init_thread = ObsInitThread(
        client,
        obs_actions=obs_actions,
        ws_open_event=ws_open_event,
        close_event=close_event,
        daemon=True,
    )

    obs_events_thread = ObsEventsThread(
        client=client,
        open_event=ws_open_event,
        start_barrier=start_barrier,
        close_event=close_event,
        error_bucket=error_bucket,
        on_disconnect=on_obs_disconnect,
        on_reconnect=on_obs_reconnect,
        reconnect_delay=obs_reconnect_delay,
        daemon=True,
    )
    obs_events_thread.add_event_handler(obs_init_thread.handle_event)

    threads = [
        midi_input_thread,
        obs_events_thread,
        obs_init_thread,
    ]

    for thread in threads:
        thread.start()

    try:
        try:
            start_barrier.wait()
        except threading.BrokenBarrierError:
            logger.error("Aborting...")
        else:
            obs_init_thread.join()
            on_ready({INFO_MIDI_INPUT_PORT_NAME: midi_input_thread.get_port_name()})
            logger.info("Ready")

            close_event.wait()
            logger.info("Stopping...")
    except KeyboardInterrupt:
        logger.info("Exiting...")
    except Exception as exc:
        error_bucket.put(exc)
    finally:
        close_event.set()

        for thread in threads:
            thread.join()

        logger.info("Stopped")

        exceptions = []

        while not error_bucket.empty():
            exceptions.append(error_bucket.get_nowait())

        if exceptions:
            raise (
                ExceptionGroup("Errors", exceptions)
                if len(exceptions) >= 2
                else exceptions[0]
            )
