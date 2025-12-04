import argparse
import logging
import logging.config
import threading

from .app import App
from .logging import LOGGING_CONFIG
from .midi_in import MIDInputThread
from .obs_client import open_obs_client
from .obs_events import ObsEventsThread
from .utils.argparse import EnvDefault
from .utils.threading import start_thread_manager

logger = logging.getLogger(__name__)


def run(midi_port: str | None, obs_port: int, obs_password: str) -> None:
    midi_ready_event = threading.Event()

    with open_obs_client(port=obs_port, password=obs_password) as client:
        app = App(client=client)

        with start_thread_manager(
            lambda close_event: MIDInputThread(
                app=app,
                port=midi_port,
                midi_ready_event=midi_ready_event,
                close_event=close_event,
                daemon=True,
            ),
            lambda close_event: ObsEventsThread(
                app=app,
                start_event=midi_ready_event,
                close_event=close_event,
                daemon=True,
            ),
        ) as thread_manager:
            midi_ready_event.wait()
            app.send_initial_request()

            try:
                thread_manager.poll_all()
            except KeyboardInterrupt:
                print("Exiting...")


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
    parser.add_argument(
        "--log-level",
        action=EnvDefault,
        env_var="LOG_LEVEL",
        required=False,
        help="Logging level",
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

    logging.config.dictConfig(LOGGING_CONFIG)

    if args.log_level is not None:
        log_level = getattr(logging, args.log_level.upper())
        logging.getLogger("obs_midi").setLevel(log_level)

    try:
        run(
            midi_port=args.midi_port,
            obs_port=args.obs_port,
            obs_password=args.obs_password,
        )
    except Exception as exc:
        if log_level == logging.DEBUG:
            logger.exception(exc)
        else:
            logger.error(exc)

        raise SystemExit(1)
