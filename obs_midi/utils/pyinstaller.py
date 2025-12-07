def pyinstaller_hints() -> None:
    # https://github.com/mido/mido/issues/219
    import mido.backends.rtmidi  # noqa: F401

    from . import logging  # noqa: F401
