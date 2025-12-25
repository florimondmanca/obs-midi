import argparse
import logging
import sys
from pathlib import Path

from ttkthemes import ThemedTk

from ..logging import LOGGING_CONFIG
from .gui import GUI

logger = logging.getLogger("obs_midi.gui")
ROOT_DIR = Path(__file__).parent.parent


def run_gui() -> None:
    parser = argparse.ArgumentParser(prog="obs-midi")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if args.reload:
        try:
            import watchfiles
        except ImportError:
            print(
                "ERROR: watchfiles is not installed, run 'make install_dev'",
                file=sys.stderr,
            )
            raise SystemExit(1)

        raise SystemExit(
            watchfiles.run_process(
                ROOT_DIR,
                target=_run_gui,
                callback=lambda changes: print("Changes detected, reloading..."),
            )
        )

    _run_gui()


def _run_gui() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)

    root = ThemedTk(
        # This should match the StartupWMClass in 'obs-midi.desktop' file so that
        # under Linux, X server knows to group the tkinter window with the launcher icon.
        className="obs-midi",
        theme="yaru",
    )

    GUI(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run_gui()
