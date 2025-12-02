import queue
import time
import threading

from .._models.midi import MIDITriggerRepository
from .._threads.obs_ws import start_obs_ws_client_thread
from .._threads.midi import start_midi_in_thread


def run(midi_port: str, obs_port: int, obs_password: str) -> None:
    q: queue.Queue[str] = queue.Queue(10)
    close_event = threading.Event()

    trigger_repository = MIDITriggerRepository()

    midi_t = start_midi_in_thread(midi_port, trigger_repository, q, close_event)
    obs_t = start_obs_ws_client_thread(
        obs_port, obs_password, trigger_repository, q, close_event
    )

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
