import logging
from typing import Callable

import mido

from .midi import ControlChange, MIDITrigger
from .obs_client import ObsClient

logger = logging.getLogger(__name__)


class App:
    def __init__(
        self, client: ObsClient, on_ready: Callable[[], None] = lambda: None
    ) -> None:
        self._client = client
        self._scene_triggers: list[tuple[MIDITrigger, str]] = []
        self._source_filter_triggers: list[tuple[MIDITrigger, str, str]] = []
        self._on_ready = on_ready

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
                        logger.info("Detected scene trigger: %s", scene_name)

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
                        logger.info("Detected filter trigger: %s", filter_name)

                self._on_ready()

    def on_midi_message(self, msg: mido.Message) -> None:
        for trigger, scene in self._scene_triggers:
            if trigger.matches(msg):
                logger.info("Switch scene: %s", scene)
                self.client.set_current_program_scene(scene)
                return

        for trigger, source_name, filter_name in self._source_filter_triggers:
            if trigger.matches(msg):
                logger.info("Show filter: %s on %s", filter_name, source_name)
                self.client.enable_filter(source_name, filter_name)
                return
