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


MIDITrigger = ControlChangeTrigger


class ObsActions:
    def __init__(self) -> None:
        self._scene_switches: list[tuple[str, MIDITrigger]] = []
        self._source_filter_toggles: list[tuple[str, str, MIDITrigger]] = []

    def on_scene_found(self, scene: str) -> None:
        if (cc := ControlChangeTrigger.parse(scene)) is not None:
            self._scene_switches.append((scene, cc))
            logger.info("Added scene switch action: %s", scene)

    def on_source_filter_found(self, *, source_name: str, filter_name: str) -> None:
        if (cc := ControlChangeTrigger.parse(filter_name)) is not None:
            self._source_filter_toggles.append((source_name, filter_name, cc))
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
