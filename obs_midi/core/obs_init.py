import logging
import threading
import time
from typing import Any

from .obs_actions import ObsActions
from .obs_client import ObsClient

logger = logging.getLogger(__name__)


class ObsInitThread(threading.Thread):
    def __init__(
        self,
        client: ObsClient,
        obs_actions: ObsActions,
        ws_open_event: threading.Event,
        close_event: threading.Event,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._client = client
        self._obs_actions = obs_actions
        self._ws_open_event = ws_open_event
        self._close_event = close_event
        self._done_event = threading.Event()
        self._request_ids: set[str] = set()

    def run(self) -> None:
        logger.info("Waiting for WebSocket to be open...")

        while True:
            if self._ws_open_event.is_set():
                break

            if self._close_event.is_set():
                logger.info("Aborting...")
                return

            time.sleep(0.2)

        self._request_ids.add(self._client.send_request("GetSceneList"))
        logger.info("Scene list request sent")

        while True:
            if self._done_event.is_set():
                logger.info("Done")
                break

            if self._close_event.is_set():
                logger.info("Stopping...")
                break

            time.sleep(0.2)

    def handle_event(self, event: dict) -> None:
        if not self._client.is_request_response(event):
            return

        self._request_ids.remove(event["d"]["requestId"])

        match event["d"]["requestType"]:
            case "GetSceneList":
                for data in event["d"]["responseData"]["scenes"]:
                    scene_name = data["sceneName"]
                    self._obs_actions.on_scene_found(scene_name)
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
                    self._obs_actions.on_source_filter_found(
                        source_name=source_name, filter_name=filter_name
                    )

        if not self._request_ids:
            self._done_event.set()
