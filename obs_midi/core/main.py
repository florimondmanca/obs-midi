import logging
import logging.config
import queue
import threading
from typing import Callable

import mido

from .midi import MIDInputOpener, MIDITrigger
from .midi_in import MIDInputThread
from .obs_client import ObsClient
from .obs_events import ObsEventsThread
from .obs_init import ObsInitThread

logger = logging.getLogger(__name__)


def run(
    midi_input_opener: MIDInputOpener,
    obs_port: int,
    obs_password: str,
    *,
    on_ready: Callable[[], None] = lambda: None,
    on_obs_disconnect: Callable[[], None] = lambda: None,
    on_obs_reconnect: Callable[[], None] = lambda: None,
    close_event: threading.Event | None = None,
) -> None:
    if close_event is None:
        close_event = threading.Event()

    error_bucket: queue.Queue[Exception] = queue.Queue()

    client = ObsClient(port=obs_port, password=obs_password)

    scene_triggers: list[tuple[MIDITrigger, str]] = []
    source_filter_triggers: list[tuple[MIDITrigger, str, str]] = []

    def on_midi_message(msg: mido.Message) -> None:
        for trigger, scene in scene_triggers:
            if trigger.matches(msg):
                logger.info("Switch scene: %s", scene)
                client.set_current_program_scene(scene)
                return

        for trigger, source_name, filter_name in source_filter_triggers:
            if trigger.matches(msg):
                logger.info("Show filter: %s on %s", filter_name, source_name)
                client.enable_filter(source_name, filter_name)
                return

    start_barrier = threading.Barrier(4)

    midi_input_thread = MIDInputThread(
        input_opener=midi_input_opener,
        start_barrier=start_barrier,
        close_event=close_event,
        error_bucket=error_bucket,
        daemon=True,
    )
    midi_input_thread.add_message_handler(on_midi_message)

    obs_init_thread = ObsInitThread(
        client,
        start_barrier=start_barrier,
        close_event=close_event,
        on_scene_trigger=scene_triggers.append,
        on_source_filter_trigger=source_filter_triggers.append,
        daemon=True,
    )

    obs_events_thread = ObsEventsThread(
        client=client,
        start_barrier=start_barrier,
        close_event=close_event,
        error_bucket=error_bucket,
        on_disconnect=on_obs_disconnect,
        on_reconnect=on_obs_reconnect,
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
            on_ready()
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
