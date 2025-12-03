import re

from ..domain.midi import ControlChange, MIDITriggerRepository
from ..domain.obs import Event, EventHandler, SceneListChangedEvent


def make_obs_event_handler(event_handlers: list[EventHandler]) -> EventHandler:
    def on_obs_event(event: Event) -> None:
        for event_handler in event_handlers:
            event_handler(event)

    return on_obs_event


def make_handle_scene_list_changed(
    trigger_repository: MIDITriggerRepository,
) -> EventHandler:
    def handle_scene_list_changed(event: Event) -> None:
        if not isinstance(event, SceneListChangedEvent):
            return

        for scene in event.scenes:
            _, sep, cc_trigger = scene.name.rpartition("::")

            if not sep:
                continue

            cc_trigger = cc_trigger.strip()

            # Example: CC46#64@8
            m = re.match(
                r"CC(?P<number>\d+)#(?P<value>\d+)@(?P<channel>\d+)", cc_trigger
            )

            if m is None:
                raise ValueError(f"Invalid CC trigger: {cc_trigger}")

            control_change = ControlChange(
                channel=int(m.group("channel")),
                number=int(m.group("number")),
                value=int(m.group("value")),
            )

            trigger_repository.add_scene_trigger(control_change, scene.name)
            # log("Scene trigger added:", cc_trigger, "=>", _)

    return handle_scene_list_changed
