import logging
import re
from dataclasses import dataclass
from typing import Optional

import mido

from .obs_client import ObsClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ControlChangeTrigger:
    text: str
    channel: int
    number: int
    value: int

    def matches(self, msg: mido.Message) -> bool:
        return (
            msg.type == "control_change"
            and msg.channel + 1 == self.channel
            and msg.control == self.number
            and msg.value == self.value
        )

    def __str__(self) -> str:
        return f"CC{self.number}#{self.value}@{self.channel}"

    @classmethod
    def parse(cls, s: str) -> Optional["ControlChangeTrigger"]:
        text, sep, encoded = s.rpartition("::")

        if not sep:
            return None

        # Example: CC46#64@8
        m = re.match(
            r"CC(?P<number>\d+)#(?P<value>\d+)@(?P<channel>\d+)", encoded.strip()
        )

        if m is None:
            return None

        return cls(
            text=text.strip(),
            channel=int(m.group("channel")),
            number=int(m.group("number")),
            value=int(m.group("value")),
        )


@dataclass(frozen=True, kw_only=True)
class ProgramChangeTrigger:
    text: str
    channel: int
    number: int

    def matches(self, msg: mido.Message) -> bool:
        return (
            msg.type == "program_change"
            and msg.channel + 1 == self.channel
            and msg.program == self.number
        )

    def __str__(self) -> str:
        return f"PC{self.number}@{self.channel}"

    @classmethod
    def parse(cls, s: str) -> Optional["ProgramChangeTrigger"]:
        text, sep, encoded = s.rpartition("::")

        if not sep:
            return None

        # Example: PC32@8
        m = re.match(r"PC(?P<number>\d+)@(?P<channel>\d+)", encoded.strip())

        if m is None:
            return None

        return cls(
            text=text.strip(),
            channel=int(m.group("channel")),
            number=int(m.group("number")),
        )


@dataclass(frozen=True, kw_only=True)
class NoteOnTrigger:
    text: str
    channel: int
    note: int
    velocity: int | None

    def matches(self, msg: mido.Message) -> bool:
        return (
            msg.type == "note_on"
            and msg.channel + 1 == self.channel
            and msg.note == self.note
            and (
                msg.velocity >= 64
                if self.velocity is None
                else msg.velocity == self.velocity
            )
        )

    def __str__(self) -> str:
        return f"On{self.note}@{self.channel}"

    @classmethod
    def parse(cls, s: str) -> Optional["NoteOnTrigger"]:
        text, sep, encoded = s.rpartition("::")

        if not sep:
            return None

        # Example: On60#127@8, On60@8
        m = re.match(
            r"On(?P<note>\d+)(#(?P<velocity>\d+))?@(?P<channel>\d+)", encoded.strip()
        )

        if m is None:
            return None

        return cls(
            text=text.strip(),
            channel=int(m.group("channel")),
            note=int(m.group("note")),
            velocity=int(v) if (v := m.group("velocity")) is not None else None,
        )


MIDITrigger = ProgramChangeTrigger | ControlChangeTrigger | NoteOnTrigger


def _parse_midi_trigger(value: str) -> MIDITrigger | None:
    if (pc := ProgramChangeTrigger.parse(value)) is not None:
        return pc

    if (cc := ControlChangeTrigger.parse(value)) is not None:
        return cc

    if (note_on := NoteOnTrigger.parse(value)) is not None:
        return note_on

    return None


class ObsActions:
    def __init__(self) -> None:
        self._scene_switches: list[tuple[str, MIDITrigger]] = []
        self._source_filter_toggles: list[tuple[str, str, MIDITrigger]] = []

    def on_scene_found(self, scene: str) -> None:
        if (trigger := _parse_midi_trigger(scene)) is not None:
            self._scene_switches.append((scene, trigger))
            logger.info("Added scene switch action: %s", scene)

    def on_source_filter_found(self, *, source_name: str, filter_name: str) -> None:
        if (trigger := _parse_midi_trigger(filter_name)) is not None:
            self._source_filter_toggles.append((source_name, filter_name, trigger))
            logger.info("Added filter toggle action: %s", filter_name)

    def process(self, msg: mido.Message, client: ObsClient) -> None:
        for scene, trigger in self._scene_switches:
            if trigger.matches(msg):
                logger.info("Switch scene: %s", scene)
                client.set_current_program_scene(scene)
                return

        for source_name, filter_name, trigger in self._source_filter_toggles:
            if trigger.matches(msg):
                logger.info("Show filter: %s on %s", filter_name, source_name)
                client.enable_filter(source_name, filter_name)
                return
