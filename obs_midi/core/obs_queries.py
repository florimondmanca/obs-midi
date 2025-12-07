import logging
import threading
from typing import Callable

from .midi import ControlChange, MIDITrigger
from .obs_client import ObsClient

logger = logging.getLogger(__name__)


class InitialOBSQuery:
    def __init__(
        self,
        client: ObsClient,
        on_scene_trigger: Callable[[tuple[MIDITrigger, str]], None] = (
            lambda args: None
        ),
        on_source_filter_trigger: Callable[[tuple[MIDITrigger, str, str]], None] = (
            lambda args: None
        ),
    ) -> None:
        self._client = client
        self._on_scene_trigger = on_scene_trigger
        self._on_source_filter_trigger = on_source_filter_trigger
        self._done_event = threading.Event()
        self._request_ids: set[str] = set()

    def send(self) -> None:
        self._request_ids.add(self._client.send_request("GetSceneList"))

    def is_done(self) -> bool:
        return self._client.has_received_response_for_requests(self._request_ids)

    def handle_event(self, event: dict) -> None:
        if not self._client.is_request_response(event):
            return

        match event["d"]["requestType"]:
            case "GetSceneList":
                for data in event["d"]["responseData"]["scenes"]:
                    scene_name = data["sceneName"]

                    if (cc := ControlChange.parse_at_end_of(scene_name)) is not None:
                        self._on_scene_trigger((cc, scene_name))
                        logger.info("Detected scene trigger: %s", scene_name)

                    self._request_ids.add(
                        self._client.send_request(
                            "GetSceneItemList", {"sceneName": scene_name}
                        )
                    )

            case "GetSceneItemList":
                for data in event["d"]["responseData"]["sceneItems"]:
                    self._request_ids.add(
                        self._client.send_request(
                            "GetSourceFilterList",
                            {"sourceName": data["sourceName"]},
                        )
                    )

            case "GetSourceFilterList":
                request_data = self._client.get_request_data(event["d"]["requestId"])

                for data in event["d"]["responseData"]["filters"]:
                    source_name = request_data["sourceName"]
                    filter_name = data["filterName"]

                    if (cc := ControlChange.parse_at_end_of(filter_name)) is not None:
                        self._on_source_filter_trigger((cc, source_name, filter_name))
                        logger.info("Detected filter trigger: %s", filter_name)

                self._done_event.set()
