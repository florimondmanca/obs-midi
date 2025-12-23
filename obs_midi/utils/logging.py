import logging
from copy import copy


class DefaultFormatter(logging.Formatter):
    black_bold = "\x1b[30;1m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[32;20m"
    green_bold = "\x1b[32;1m"
    yellow = "\x1b[33;20m"
    blue = "\x1b[34;20m"
    purple = "\x1b[35;20m"
    purple_bold = "\x1b[35;1m"
    reset = "\x1b[0m"

    LEVEL_COLOR = {
        "DEBUG": purple,
        "INFO": blue,
        "WARNING": yellow,
        "ERROR": red,
        "CRITICAL": bold_red,
    }

    LOGGER_COLOR = {
        "obs_midi.cli": yellow,
        "obs_midi.gui": yellow,
        "obs_midi.core.obs_events": purple_bold,
        "obs_midi.core.obs_init": purple_bold,
        "obs_midi.core.midi_in": green_bold,
        "obs_midi.core.main": black_bold,
    }

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
    ):
        super().__init__(fmt=fmt, datefmt=datefmt)

    def formatMessage(self, record: logging.LogRecord) -> str:
        recordcopy = copy(record)

        level_color = self.LEVEL_COLOR.get(recordcopy.levelname)
        levelname = (
            f"{level_color}{recordcopy.levelname}{self.reset}"
            if level_color
            else recordcopy.levelname
        )

        logger_color = self.LOGGER_COLOR.get(recordcopy.name)
        name = (
            f"{logger_color}{recordcopy.name}{self.reset}"
            if logger_color
            else recordcopy.name
        )

        prefix = f"[{name}] {levelname}"
        recordcopy.__dict__["levelprefix"] = prefix + ":"
        return super().formatMessage(recordcopy)
