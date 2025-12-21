import argparse
import logging
import logging.config

from .core.main import run
from .core.midi import rtmidi_input_opener
from .logging import LOGGING_CONFIG
from .utils.argparse import EnvDefault

logger = logging.getLogger(__name__)


def run_cli() -> None:
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

    args = parser.parse_args()

    logging.config.dictConfig(LOGGING_CONFIG)

    try:
        run(
            midi_input_opener=rtmidi_input_opener(
                port=args.midi_port, interactive=True
            ),
            obs_port=args.obs_port,
            obs_password=args.obs_password,
        )
    except Exception as exc:
        logger.error(exc)
        raise SystemExit(1)


if __name__ == "__main__":
    run_cli()
