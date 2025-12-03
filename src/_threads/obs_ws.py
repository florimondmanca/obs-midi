import base64
import hashlib
import json
import queue
import re
import threading
import time
import uuid
from typing import Iterator

import websockets
import websockets.sync.client

from .._models.command import (
    Command,
    ShowFilterCommand,
    SwitchSceneCommand,
)
from .._models.midi import ControlChange, MIDITrigger, MIDITriggerRepository


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


def _parse_cc_trigger(trigger: str) -> ControlChange:
    # Example: CC46#64@8
    m = re.match(r"CC(?P<number>\d+)#(?P<value>\d+)@(?P<channel>\d+)", trigger)

    if m is None:
        raise ValueError(f"Invalid CC trigger: {trigger}")

    return ControlChange(
        channel=int(m.group("channel")),
        number=int(m.group("number")),
        value=int(m.group("value")),
    )


def _parse_scene_triggers(scenes: list[dict]) -> list[tuple[MIDITrigger, str]]:
    triggers = []

    for scene in scenes:
        name: str = scene["sceneName"]

        name, sep, trigger = name.rpartition("::")

        if not sep:
            continue

        name = name.strip()
        trigger = trigger.strip()

        cc = _parse_cc_trigger(trigger)
        triggers.append((cc, name))

    return triggers


def _run_event_receiver(
    client: ObsClient,
    trigger_repository: MIDITriggerRepository,
    close_event: threading.Event,
) -> None:
    def log(*values: object) -> None:
        print("[ws][events]", *values)

    try:
        log("Started")

        for event in client.iter_events():
            if close_event.is_set():
                break

            if event is None:
                continue

            # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#getscenelist
            if (
                event["op"] == 7
                and event["d"].get("requestType") == "GetSceneList"
                and event["d"].get("requestStatus", {}).get("result")
            ):
                triggers = _parse_scene_triggers(event["d"]["responseData"]["scenes"])

                for trigger, name in triggers:
                    trigger_repository.add_scene_trigger(trigger, name)
                    log("Scene trigger added:", trigger, "=>", name)

        log("Stopped")
    except Exception as exc:
        log("ERROR:", exc)
        raise


def _run_request_sender(
    client: ObsClient, q: queue.Queue[Command], close_event: threading.Event
) -> None:
    def log(*values: object) -> None:
        print("[ws][requests]", *values)

    try:
        log("Started")

        client.request_scene_list()

        while not close_event.is_set():
            try:
                command = q.get(timeout=1)
            except queue.Empty:
                continue

            match command:
                case SwitchSceneCommand():
                    scene = command.scene
                    log("Switch scene:", scene)
                    client.set_current_program_scene(scene)
                case ShowFilterCommand():
                    source = command.source
                    filtername = command.filter
                    log("Show filter:", source, filtername)
                    client.enable_filter(source, filtername)

        log("Stopped")
    except Exception as exc:
        log("ERROR:", exc)
        raise


def run_obs_websocket_client(
    port: int,
    password: str,
    trigger_repository: MIDITriggerRepository,
    q: queue.Queue,
    close_event: threading.Event,
) -> None:
    def log(*values: object) -> None:
        print("[ws]", *values)

    try:
        with websockets.sync.client.connect(f"ws://localhost:{port}") as ws:
            client = ObsClient(ws)
            client.authenticate(password)
            log("Connected")

            events_t = threading.Thread(
                target=_run_event_receiver,
                args=(client, trigger_repository, close_event),
            )
            events_t.daemon = True
            events_t.start()

            requests_t = threading.Thread(
                target=_run_request_sender, args=(client, q, close_event)
            )
            requests_t.daemon = True
            requests_t.start()

            threads = [events_t, requests_t]

            while any(t.is_alive() for t in threads):
                time.sleep(0.2)

            for t in threads:
                t.join()

        log("Stopped")

    except Exception as exc:
        log("ERROR:", exc)


def start_obs_ws_client_thread(
    port: int,
    password: str,
    trigger_repository: MIDITriggerRepository,
    q: queue.Queue,
    close_event: threading.Event,
) -> threading.Thread:
    thread = threading.Thread(
        target=run_obs_websocket_client,
        args=(port, password, trigger_repository, q, close_event),
    )
    thread.daemon = True
    thread.start()
    return thread
