import argparse
import queue
import threading
import time

from src.application.event_handlers import (
    make_handle_scene_list_changed,
    make_obs_event_handler,
)
from src.domain.command import Command
from src.domain.midi import MIDITriggerRepository
from src.infrastructure.adapters.midi import get_midi_ports
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
        while all(t.is_alive() for t in threads):
            time.sleep(0.2)
        _close_threads()
    except KeyboardInterrupt:
        print("Exiting...")
        _close_threads()


def list_ports() -> None:
    for port in get_midi_ports():
        print(port)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_list_ports = subparsers.add_parser("list", help="List MIDI ports")
    parser_list_ports.set_defaults(func=lambda args: list_ports())

    parser_listen = subparsers.add_parser("run", help="Run MIDI / obs-websocket bridge")
    parser_listen.add_argument("-p", "--midi-port", help="MIDI port")
    parser_listen.add_argument("--obs-port", help="obs-websocket port", default=4455)
    parser_listen.add_argument("--obs-password", help="obs-websocket password")
    parser_listen.set_defaults(
        func=lambda args: run(
            midi_port=args.midi_port,
            obs_port=args.obs_port,
            obs_password=args.obs_password,
        )
    )

    args = parser.parse_args()

    try:
        func = args.func
    except AttributeError:
        parser.print_help()
        raise SystemExit(1)

    func(args)
