import queue
import threading
import time

from src.application.event_handlers import (
    make_handle_scene_list_changed,
    make_obs_event_handler,
)
from src.domain.command import Command
from src.domain.midi import MIDITriggerRepository
from src.infrastructure.threads.midi import MIDIListener
from src.infrastructure.threads.obs_ws import ObsWebSocketController


def run(midi_port: str, obs_port: int, obs_password: str) -> None:
    midi_queue: queue.Queue[Command] = queue.Queue(10)
    close_event = threading.Event()

    trigger_repository = MIDITriggerRepository()

    midi_listener = MIDIListener(
        port=midi_port,
        trigger_repository=trigger_repository,
        q=midi_queue,
    )
    midi_t = midi_listener.start_thread(close_event=close_event)

    on_obs_event = make_obs_event_handler(
        [make_handle_scene_list_changed(trigger_repository)]
    )

    obs_controller = ObsWebSocketController(
        port=obs_port,
        password=obs_password,
        command_queue=midi_queue,
        on_event=on_obs_event,
    )
    obs_t = obs_controller.start_thread(close_event=close_event)

    threads = [midi_t, obs_t]

    def _close_threads() -> None:
        close_event.set()

        for t in threads:
            t.join()

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(0.2)
        _close_threads()
    except KeyboardInterrupt:
        print("Exiting...")
        _close_threads()
