import argparse
import logging
import logging.config

from .core.main import run
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
    parser.add_argument(
        "--log-level",
        action=EnvDefault,
        env_var="LOG_LEVEL",
        required=False,
        help="Logging level",
    )

    args = parser.parse_args()

    if args.log_level is not None:
        log_level = getattr(logging, args.log_level.upper())
        logging.getLogger("obs_midi").setLevel(log_level)

    try:
        run(
            midi_port=args.midi_port,
            obs_port=args.obs_port,
            obs_password=args.obs_password,
            interactive=True,
        )
    except Exception as exc:
        if log_level == logging.DEBUG:
            logger.exception(exc)
        else:
            logger.error("Application error: %s", exc)

        raise SystemExit(1)


if __name__ == "__main__":
    logging.config.dictConfig(LOGGING_CONFIG)
    run_cli()
