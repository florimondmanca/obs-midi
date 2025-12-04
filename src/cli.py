import argparse
import threading
import time

import websockets.sync.client

from .app import App
from .midi_in import MIDInputThread
from .obs_client import open_obs_client
from .obs_events import ObsEventsThread
from .utils.argparse import EnvDefault


def log(*values: object) -> None:
    print("[main]", *values)


def run(midi_port: str | None, obs_port: int, obs_password: str) -> None:
    midi_ready_event = threading.Event()
    close_event = threading.Event()

    with open_obs_client(port=obs_port, password=obs_password) as client:
        app = App(client=client)

        threads = [
            MIDInputThread(
                app=app,
                port=midi_port,
                midi_ready_event=midi_ready_event,
                close_event=close_event,
            ),
            ObsEventsThread(
                app=app, start_event=midi_ready_event, close_event=close_event
            ),
        ]

        for thread in threads:
            thread.daemon = True
            thread.start()

        midi_ready_event.wait()
        app.send_initial_request()

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Control OBS with MIDI via obs-websocket",
    )

    parser.add_argument(
        "-p",
        "--midi-port",
        action=EnvDefault,
        env_var="MIDI_PORT",
        required=False,
        help="MIDI port",
    )
    parser.add_argument(
        "--obs-port",
        action=EnvDefault,
        env_var="OBS_PORT",
        help="obs-websocket port",
    )
    parser.add_argument(
        "--obs-password",
        action=EnvDefault,
        env_var="OBS_PASSWORD",
        help="obs-websocket password",
    )
    parser.set_defaults(
        impl=(
            parser,
            lambda args: run(
                midi_port=args.midi_port,
                obs_port=args.obs_port,
                obs_password=args.obs_password,
            ),
        )
    )

    args = parser.parse_args()

    try:
        run(
            midi_port=args.midi_port,
            obs_port=args.obs_port,
            obs_password=args.obs_password,
        )
    except Exception as exc:
        log("ERROR:", exc)
        raise SystemExit(1)
