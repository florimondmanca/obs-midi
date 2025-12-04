LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "obs_midi.utils.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "obs_midi": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
}
