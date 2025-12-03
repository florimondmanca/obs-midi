import base64
import hashlib
import json
import uuid
from typing import Iterator

import websockets


class ObsClient:
    # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md

    def __init__(self, ws: websockets.sync.connection.Connection) -> None:
        self._ws = ws

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
            yield event

    def request_scene_list(self) -> None:
        # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#getscenelist
        msg = {
            "op": 6,
            "d": {
                "requestType": "GetSceneList",
                "requestId": str(uuid.uuid4()),
            },
        }

        self._ws.send(json.dumps(msg))

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
