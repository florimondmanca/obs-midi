import argparse
import base64
import hashlib
import json
import pathlib
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal

import mido
import rtmidi
from rtmidi.midiutil import open_midiinput
from websockets.sync.client import connect


def list_ports(args: Any) -> None:
    with rtmidi.MidiOut() as midiout:
        ports = midiout.get_ports()
        for port in ports:
            print(port)


@dataclass(frozen=True, kw_only=True)
class MIDIMapping:
    name: str | None = None
    type: Literal["CC"]
    channel: int | None = None
    number: int
    value: int
    action: Literal["SwitchScene", "ShowFilter"]
    scene: str | None = None
    source: str | None = None
    filter: str | None = None


class MIDIInputHandler:
    # https://github.com/SpotlightKid/python-rtmidi/blob/master/examples/midi2command/midi2command.py

    def __init__(self, port_name: str, q: queue.Queue) -> None:
        self._port_name = port_name
        self._q = q

        config = json.loads(pathlib.Path("config.json").read_text())
        self._default_channel = config["default_channel"]
        self._mappings = [MIDIMapping(**row) for row in config["mappings"]]

    # https://spotlightkid.github.io/python-rtmidi/rtmidi.html#rtmidi.MidiIn.set_callback
    def __call__(self, event: tuple, data: object = None) -> None:
        msg_bytes, _delta_time = event

        msg: mido.Message = mido.parse(msg_bytes)
        print(f"[MIDI] Msg: {msg}")

        if not msg.is_cc():
            return

        for mapping in self._mappings:
            if mapping.type != "CC":
                continue

            if mapping.number != msg.control:
                continue

            channel = (
                mapping.channel
                if mapping.channel is not None
                else self._default_channel
            )

            # Raw MIDI channel is 0-based
            if msg.channel + 1 != channel:
                continue

            if msg.value == mapping.value:
                self._q.put(
                    {
                        "action": mapping.action,
                        "scene": mapping.scene,
                        "source": mapping.source,
                        "filter": mapping.filter,
                    }
                )
                break


def _listen_midi(
    port: str | None, q: queue.Queue, ready_event: threading.Event
) -> None:
    print(f"Selected port: {port}")

    try:
        midiin, port_name = open_midiinput(
            port,
            client_name="python-obs-midi",
            port_name="MIDI Input",
        )
    except Exception as exc:
        print("[MIDI] ERROR:", exc)
        ready_event.set()
        raise

    midiin.set_callback(MIDIInputHandler(port_name, q))

    with midiin:
        print("[MIDI] Listening for messages...")
        ready_event.set()
        try:
            while True:
                time.sleep(1)
        except Exception as exc:
            print("[MIDI] ERROR:", exc)
            raise
        except KeyboardInterrupt:
            print("[MIDI] Closing...")
            pass


def listen(args: Any) -> None:
    q: queue.Queue[str] = queue.Queue(10)

    ready_event = threading.Event()
    midi_t = threading.Thread(target=_listen_midi, args=(args.port, q, ready_event))
    midi_t.daemon = True
    midi_t.start()
    ready_event.wait()

    midi_obs = threading.Thread(target=_obs_websocket_client, args=(4455, q))
    midi_obs.daemon = True
    midi_obs.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")


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


def _obs_websocket_client(port: int, q: queue.Queue):
    password = "alternatepopper14"
    try:
        with connect(f"ws://localhost:{port}") as ws:
            obs_client = ObsClient(ws)
            obs_client.authenticate(password)
            print("[ws] Connected")
            try:
                while True:
                    msg = q.get()

                    if msg["action"] == "SwitchScene":
                        scene = msg["scene"]
                        print("[ws] Switch scene:", scene)
                        obs_client.set_current_program_scene(scene)

                    if msg["action"] == "ShowFilter":
                        source = msg["source"]
                        filtername = msg["filter"]
                        print("[ws] Show filter:", source, filtername)
                        obs_client.enable_filter(source, filtername)

            except KeyboardInterrupt:
                print("[ws] Closing...")
    except Exception as exc:
        print("[ws] ERROR:", exc)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_list_ports = subparsers.add_parser("list", help="List MIDI ports")
    parser_list_ports.set_defaults(func=list_ports)

    parser_listen = subparsers.add_parser("listen", help="Listen on MIDI port")
    parser_listen.add_argument("-p", "--port")

    parser_listen.set_defaults(func=listen)

    args = parser.parse_args()

    try:
        func = args.func
    except AttributeError:
        parser.print_help()
        raise SystemExit(1)

    func(args)
