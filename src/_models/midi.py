from dataclasses import dataclass

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


MIDITrigger = ControlChange


class MIDITriggerRepository:
    def __init__(self) -> None:
        self._scene_triggers: list[tuple[MIDITrigger, str]] = []

    def add_scene_trigger(self, trigger: MIDITrigger, scene: str) -> None:
        self._scene_triggers.append((trigger, scene))

    def match_scene(self, msg: mido.Message) -> str | None:
        for trigger, scene in self._scene_triggers:
            if trigger.matches(msg):
                return scene

        return None
