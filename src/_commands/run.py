import queue
import time
import threading

from .._threads.obs_ws import start_obs_ws_client_thread
from .._threads.midi import start_midi_in_thread


def run(midi_port: str, obs_port: int, obs_password: str) -> None:
    q: queue.Queue[str] = queue.Queue(10)
    close_event = threading.Event()

    midi_t = start_midi_in_thread(midi_port, q, close_event)
    obs_t = start_obs_ws_client_thread(obs_port, obs_password, q, close_event)

    try:
        while midi_t.is_alive() and obs_t.is_alive():
            time.sleep(0.2)

        close_event.set()
        midi_t.join()
        obs_t.join()
    except KeyboardInterrupt:
        print("Exiting...")
