import re
from dataclasses import dataclass
from typing import Optional

import mido


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
