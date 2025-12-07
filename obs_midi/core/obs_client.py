import base64
import hashlib
import json
import logging
import uuid
from typing import Any, Iterator

import websockets
import websockets.sync.connection

logger = logging.getLogger(__name__)


def open_obs_client(port: int, password: str) -> "ObsClient":
    ws = websockets.sync.client.connect(f"ws://localhost:{port}")
    client = ObsClient(ws)
    client.authenticate(password)
    return client


class ObsClient:
    # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md

    REQUEST_GET_SCENE_LIST = "GetSceneList"

    def __init__(self, ws: websockets.sync.connection.Connection) -> None:
        self._ws = ws
        self._request_data_entries: dict[str, dict] = {}
        self._request_ids_with_response: set[str] = set()

    def __enter__(self) -> "ObsClient":
        return self

    def __exit__(self, *args: Any) -> None:
        return self._ws.__exit__(*args)

    def authenticate(self, password: str) -> None:
        server_hello = json.loads(self._ws.recv())

        secret = base64.b64encode(
            hashlib.sha256(
                (password + server_hello["d"]["authentication"]["salt"]).encode()
            ).digest()
        )

        auth = base64.b64encode(
            hashlib.sha256(
                secret + server_hello["d"]["authentication"]["challenge"].encode()
            ).digest()
        ).decode()

        payload = {
            "op": 1,
            "d": {"rpcVersion": 1, "authentication": auth},
        }

        self._ws.send(json.dumps(payload))

    def iter_events(self) -> Iterator[dict | None]:
        while True:
            try:
                message = self._ws.recv(timeout=0.2)
            except TimeoutError:
                yield None
                continue

            event = json.loads(message)

            if self.is_request_response(event):
                self._request_ids_with_response.add(event["d"]["requestId"])

            yield event

    def has_received_response_for_requests(self, request_ids: set[str]) -> bool:
        return all(
            request_id in self._request_ids_with_response for request_id in request_ids
        )

    def get_request_data(self, request_id: str) -> dict:
        return self._request_data_entries.get(request_id, {})

    def is_request_response(self, event: dict) -> bool:
        return event["op"] == 7 and event["d"].get("requestStatus", {}).get("result")

    def send_request(self, request_type: str, request_data: dict | None = None) -> str:
        # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#getscenelist
        request_id = str(uuid.uuid4())

        msg: dict = {
            "op": 6,
            "d": {
                "requestType": request_type,
                "requestId": request_id,
            },
        }

        if request_data is not None:
            msg["d"]["requestData"] = request_data
            self._request_data_entries[request_id] = request_data

        self._ws.send(json.dumps(msg))

        return request_id

    def set_current_program_scene(self, name: str) -> None:
        # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#setcurrentscenecollection
        msg = {
            "op": 6,
            "d": {
                "requestType": "SetCurrentProgramScene",
                "requestId": str(uuid.uuid4()),
                "requestData": {
                    "sceneName": name,
                },
            },
        }

        self._ws.send(json.dumps(msg))

    def enable_filter(self, source: str, filtername: str) -> None:
        # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#setsourcefilterenabled
        msg = {
            "op": 6,
            "d": {
                "requestType": "SetSourceFilterEnabled",
                "requestId": str(uuid.uuid4()),
                "requestData": {
                    "sourceName": source,
                    "filterName": filtername,
                    "filterEnabled": True,
                },
            },
        }

        self._ws.send(json.dumps(msg))
