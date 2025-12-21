import contextlib
import logging
import re
from dataclasses import dataclass
from typing import Callable, ContextManager, Iterator, Optional

import mido
from rtmidi.midiutil import open_midiinput

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ControlChange:
    channel: int
    number: int
    value: int

    def matches(self, msg: mido.Message) -> bool:
        if not msg.is_cc(self.number):
            return False

        if msg.channel + 1 != self.channel:
            return False

        if msg.value != self.value:
            return False

        return True

    def __str__(self) -> str:
        return f"CC{self.number}#{self.value}@{self.channel}"

    @classmethod
    def parse_at_end_of(cls, s: str) -> Optional["ControlChange"]:
        _, sep, cc_trigger = s.rpartition("::")

        if not sep:
            return None

        cc_trigger = cc_trigger.strip()

        # Example: CC46#64@8
        m = re.match(r"CC(?P<number>\d+)#(?P<value>\d+)@(?P<channel>\d+)", cc_trigger)

        if m is None:
            return None

        return cls(
            channel=int(m.group("channel")),
            number=int(m.group("number")),
            value=int(m.group("value")),
        )


MIDITrigger = ControlChange

MIDICallback = Callable[[mido.Message], None]
MIDInputOpener = Callable[[MIDICallback], ContextManager[None]]


def rtmidi_input_opener(
    *,
    port: str | None,
    interactive: bool,
) -> MIDInputOpener:
    @contextlib.contextmanager
    def _open_rtmidi_input(callback: MIDICallback) -> Iterator[None]:
        logger.debug("Selected port: %s", port)

        midi_input, port_name = open_midiinput(
            port,
            use_virtual=not interactive,
            client_name="OBS MIDI",
            port_name="Midi In",
            interactive=interactive,
        )

        # https://spotlightkid.github.io/python-rtmidi/rtmidi.html#rtmidi.MidiIn.set_callback
        @midi_input.set_callback
        def midi_callback(event: tuple, data: object = None) -> None:
            try:
                msg_bytes, _ = event
                msg: mido.Message = mido.parse(msg_bytes)
                callback(msg)
            except Exception as exc:
                logger.error(exc)
                raise

        with midi_input:
            yield

    return _open_rtmidi_input
