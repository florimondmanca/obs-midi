import base64
import hashlib
import json
import queue
import threading
import time
import uuid

from .._models.command import (
    Command,
    CommandActionEnum,
    SwitchSceneCommand,
    ShowFilterCommand,
)
import websockets
import websockets.sync.client


class ObsClient:
    # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md

    def __init__(self, ws) -> None:
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
            "d": {"rpcVersion": 1, "eventSubscriptions": 0, "authentication": auth},
        }

        self._ws.send(json.dumps(payload))

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


def _run_sender(
    client: ObsClient, q: queue.Queue[Command], close_event: threading.Event
) -> None:
    try:
        print("[ws][sender] Started")

        while not close_event.is_set():
            try:
                command = q.get(timeout=1)
            except queue.Empty:
                continue

            match command:
                case SwitchSceneCommand():
                    scene = command.scene
                    print("[ws][sender] Switch scene:", scene)
                    client.set_current_program_scene(scene)
                case ShowFilterCommand():
                    source = command.source
                    filtername = command.filter
                    print("[ws][sender] Show filter:", source, filtername)
                    client.enable_filter(source, filtername)

        print("[ws][sender] Stopped")
    except Exception as exc:
        print("[ws][sender] ERROR:", exc)
        raise


def run_obs_websocket_client(
    port: int, password: str, q: queue.Queue, close_event: threading.Event
) -> None:
    try:
        with websockets.sync.client.connect(f"ws://localhost:{port}") as ws:
            client = ObsClient(ws)
            client.authenticate(password)
            print("[ws] Connected")

            sender_t = threading.Thread(
                target=_run_sender, args=(client, q, close_event)
            )
            sender_t.daemon = True
            sender_t.start()

            while sender_t.is_alive():
                time.sleep(0.2)

            sender_t.join()

    except Exception as exc:
        print("[ws] ERROR:", exc)


def start_obs_ws_client_thread(
    port: int,
    password: str,
    q: queue.Queue,
    close_event: threading.Event,
) -> threading.Thread:
    thread = threading.Thread(
        target=run_obs_websocket_client, args=(port, password, q, close_event)
    )
    thread.daemon = True
    thread.start()
    return thread
