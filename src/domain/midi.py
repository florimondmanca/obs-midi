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


class MIDITriggerRepository:
    def __init__(self) -> None:
        self._scene_triggers: list[tuple[MIDITrigger, str]] = []
        self._source_filter_triggers: list[tuple[MIDITrigger, str, str]] = []

    def add_scene_trigger(self, trigger: MIDITrigger, scene: str) -> None:
        self._scene_triggers.append((trigger, scene))

    def match_scene(self, msg: mido.Message) -> str | None:
        for trigger, scene in self._scene_triggers:
            if trigger.matches(msg):
                return scene

        return None

    def add_source_filter_trigger(
        self, trigger: MIDITrigger, source_name: str, filter_name: str
    ) -> None:
        self._source_filter_triggers.append((trigger, source_name, filter_name))

    def match_source_filter(self, msg: mido.Message) -> tuple[str, str] | None:
        for trigger, source_name, filter_name in self._source_filter_triggers:
            if trigger.matches(msg):
                return (source_name, filter_name)

        return None
