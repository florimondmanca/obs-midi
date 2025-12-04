from dataclasses import dataclass

import mido

from .midi import ControlChange, MIDITrigger
from .obs_client import ObsClient


def log(*values: object) -> None:
    print("[app]", *values)


@dataclass(frozen=True, kw_only=True)
class SwitchSceneCommand:
    scene: str


@dataclass(frozen=True, kw_only=True)
class ShowFilterCommand:
    source: str
    filter: str


Command = SwitchSceneCommand | ShowFilterCommand


class App:
    def __init__(self, client: ObsClient) -> None:
        self._client = client
        self._scene_triggers: list[tuple[MIDITrigger, str]] = []
        self._source_filter_triggers: list[tuple[MIDITrigger, str, str]] = []

    @property
    def client(self) -> ObsClient:
        return self._client

    def send_initial_request(self) -> None:
        self.client.send_request("GetSceneList")

    def on_response(self, event: dict, request_data: dict) -> None:
        match event["d"]["requestType"]:
            case "GetSceneList":
                for data in event["d"]["responseData"]["scenes"]:
                    scene_name = data["sceneName"]

                    if (cc := ControlChange.parse_at_end_of(scene_name)) is not None:
                        self._scene_triggers.append((cc, scene_name))
                        log("Detected scene trigger:", scene_name)

                    self.client.send_request(
                        "GetSceneItemList", {"sceneName": scene_name}
                    )

            case "GetSceneItemList":
                for data in event["d"]["responseData"]["sceneItems"]:
                    self.client.send_request(
                        "GetSourceFilterList",
                        {"sourceName": data["sourceName"]},
                    )

            case "GetSourceFilterList":
                for data in event["d"]["responseData"]["filters"]:
                    source_name = request_data["sourceName"]
                    filter_name = data["filterName"]

                    if (cc := ControlChange.parse_at_end_of(filter_name)) is not None:
                        self._source_filter_triggers.append(
                            (cc, source_name, filter_name)
                        )
                        log("Detected filter trigger:", filter_name)

    def on_midi_message(self, msg: mido.Message) -> None:
        for trigger, scene in self._scene_triggers:
            if trigger.matches(msg):
                log("Switch scene:", scene)
                self.client.set_current_program_scene(scene)
                return

        for trigger, source_name, filter_name in self._source_filter_triggers:
            if trigger.matches(msg):
                log("Show filter:", source_name, filter_name)
                self.client.enable_filter(source_name, filter_name)
                return
