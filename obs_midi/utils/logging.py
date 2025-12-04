import logging
from copy import copy


class DefaultFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
    ):
        super().__init__(fmt=fmt, datefmt=datefmt)

    def formatMessage(self, record: logging.LogRecord) -> str:
        recordcopy = copy(record)
        prefix = f"{recordcopy.levelname}: {recordcopy.name}"
        seperator = " " * (8 - len(prefix))
        recordcopy.__dict__["levelprefix"] = prefix + ": " + seperator
        return super().formatMessage(recordcopy)
