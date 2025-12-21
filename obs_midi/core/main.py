import logging
import logging.config
import queue
import threading
import time
from typing import Callable

import mido

from .midi import MIDInputOpener, MIDITrigger
from .midi_in import MIDInputThread
from .obs_client import open_obs_client
from .obs_events import ObsEventsThread
from .obs_queries import InitialOBSQuery

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
    midi_ready_event = threading.Event()

    if close_event is None:
        close_event = threading.Event()

    error_bucket: queue.Queue[Exception] = queue.Queue()

    with open_obs_client(port=obs_port, password=obs_password) as client:
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

        midi_input_thread = MIDInputThread(
            input_opener=midi_input_opener,
            ready_event=midi_ready_event,
            close_event=close_event,
            error_bucket=error_bucket,
            daemon=True,
        )
        midi_input_thread.add_message_handler(on_midi_message)

        initial_obs_query = InitialOBSQuery(
            client,
            on_scene_trigger=scene_triggers.append,
            on_source_filter_trigger=source_filter_triggers.append,
        )

        obs_events_thread = ObsEventsThread(
            client=client,
            start_event=midi_ready_event,
            close_event=close_event,
            error_bucket=error_bucket,
            on_disconnect=on_obs_disconnect,
            on_reconnect=on_obs_reconnect,
            daemon=True,
        )
        obs_events_thread.add_event_handler(initial_obs_query.handle_event)

        threads = [
            midi_input_thread,
            obs_events_thread,
        ]

        for thread in threads:
            thread.start()

        def flush_error_bucket() -> None:
            try:
                exc = error_bucket.get_nowait()
            except queue.Empty:
                pass
            else:
                raise exc

        def close_all_threads() -> None:
            close_event.set()
            for thread in threads:
                thread.join()

        try:
            midi_ready_event.wait()
            logger.info("MIDI input is ready")

            if not all(t.is_alive() for t in threads):
                logger.info("Some threads dead after MIDI input ready, terminating...")
                flush_error_bucket()
                return

            logger.info("Sending initial OBS query...")
            initial_obs_query.send()
            logger.info("Initial OBS query sent")

            while not initial_obs_query.is_done():
                time.sleep(0.2)

            logger.info("Initial OBS query finished")

            if not all(t.is_alive() for t in threads):
                logger.info(
                    "Some threads dead after OBS query finished, terminating..."
                )
                flush_error_bucket()
                return

            logger.info("Application is ready")
            on_ready()

            while True:
                if not all(t.is_alive() for t in threads):
                    logger.info("Some threads dead during main loop, terminating...")
                    flush_error_bucket()
                    return

                time.sleep(0.2)

                if close_event.is_set():
                    logger.info("Received close event in main loop, terminating...")
                    flush_error_bucket()
                    return
        except KeyboardInterrupt:
            logger.info("Exiting...")
        except Exception:
            raise
        finally:
            logger.info("Closing all threads...")
            close_all_threads()
            logger.info("Threads closed")
