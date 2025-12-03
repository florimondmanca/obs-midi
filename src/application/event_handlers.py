from ..domain.midi import ControlChange, MIDITriggerRepository
from ..domain.obs import (
    Event,
    EventHandler,
    FilterListReceivedEvent,
    SceneListReceivedEvent,
)


def log(*values: object) -> None:
    print("[MIDI]", *values)


def make_obs_event_handler(event_handlers: list[EventHandler]) -> EventHandler:
    def on_obs_event(event: Event) -> None:
        for event_handler in event_handlers:
            event_handler(event)

    return on_obs_event


def make_handle_scene_list_received(
    trigger_repository: MIDITriggerRepository,
) -> EventHandler:
    def handle_scene_list_received(event: Event) -> None:
        if not isinstance(event, SceneListReceivedEvent):
            return

        for scene in event.scenes:
            if (cc := ControlChange.parse_at_end_of(scene.name)) is not None:
                trigger_repository.add_scene_trigger(cc, scene.name)
                log("Detected scene trigger:", scene.name)

    return handle_scene_list_received


def make_handle_filter_list_received(
    trigger_repository: MIDITriggerRepository,
) -> EventHandler:
    def handle_filter_list_received(event: Event) -> None:
        if not isinstance(event, FilterListReceivedEvent):
            return

        for filter in event.filters:
            if (cc := ControlChange.parse_at_end_of(filter.name)) is not None:
                trigger_repository.add_scene_trigger(cc, filter.name)
                log("Detected filter trigger:", filter.name)

    return handle_filter_list_received
