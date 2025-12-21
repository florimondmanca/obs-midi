import base64
import hashlib
import json
import logging
import sys
import uuid
from contextlib import contextmanager
from typing import Iterator

import websockets
from websockets.sync.client import Connection, connect

logger = logging.getLogger(__name__)


class ObsDisconnect(Exception):
    pass


@contextmanager
def create_obs_client(port: int, password: str) -> Iterator["ObsClient"]:
    client = ObsClient(port=port, password=password)

    try:
        client.connect()
        yield client
    finally:
        client.close()


class ObsClient:
    # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md

    REQUEST_GET_SCENE_LIST = "GetSceneList"

    def __init__(self, port: int, password: str) -> None:
        self._port = port
        self._password = password
        self._ws: Connection | None = None
        self._request_data_entries: dict[str, dict] = {}
        self._request_ids_with_response: set[str] = set()

    def connect(self) -> None:
        assert self._ws is None, "Already connected"
        self._ws = connect(f"ws://localhost:{self._port}")
        try:
            self._authenticate()
        except ObsDisconnect:
            raise

    def reconnect(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None

        self.connect()

    def close(self) -> None:
        if self._ws is None:
            return

        exc_name, exc, _ = sys.exc_info()
        close_code = (
            websockets.CloseCode.NORMAL_CLOSURE
            if exc is None
            else websockets.CloseCode.INTERNAL_ERROR
        )
        self._ws.close(close_code)
        self._ws = None

    def _authenticate(self) -> None:
        server_hello = json.loads(self._recv(None))

        secret = base64.b64encode(
            hashlib.sha256(
                (self._password + server_hello["d"]["authentication"]["salt"]).encode()
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

        self._send(json.dumps(payload))

        try:
            self._recv(None)
        except ObsDisconnect:
            # Authentication failed
            raise

    def _recv(self, timeout: float | None) -> str | bytes:
        assert self._ws is not None, "Not connected"

        try:
            return self._ws.recv(timeout)
        except TimeoutError:
            return ""
        except websockets.ConnectionClosed:
            self._ws = None
            raise ObsDisconnect()

    def _send(self, msg: str) -> None:
        assert self._ws is not None, "Not connected"

        try:
            self._ws.send(msg)
        except websockets.ConnectionClosed:
            self._ws = None
            raise ObsDisconnect()

    def iter_events(self, poll_interval: float | None) -> Iterator[dict | None]:
        while True:
            msg = self._recv(timeout=poll_interval)

            if not msg:
                yield None
                continue

            yield json.loads(msg)

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

        self._send(json.dumps(msg))

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

        self._send(json.dumps(msg))

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

        self._send(json.dumps(msg))
