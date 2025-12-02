import json
import pathlib
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Literal

import mido
from rtmidi.midiutil import open_midiinput

from .._models.command import (
    CommandActionEnum,
    Command,
    SwitchSceneCommand,
    ShowFilterCommand,
)


@dataclass(frozen=True, kw_only=True)
class MIDIMapping:
    name: str | None = None
    type: Literal["CC"]
    channel: int | None = None
    number: int
    value: int
    action: CommandActionEnum
    data: dict = field(default_factory=dict)


class MIDIInputHandler:
    # https://github.com/SpotlightKid/python-rtmidi/blob/master/examples/midi2command/midi2command.py

    def __init__(self, port_name: str, config: dict, q: queue.Queue) -> None:
        self._port_name = port_name
        self._q = q
        self._default_channel = config["default_channel"]

        mappings = []

        for row in config["mappings"]:
            data = row.get("data", {})

            match row["action"]:
                case CommandActionEnum.SWITCH_SCENE:
                    if not data.get("scene"):
                        raise ValueError("'scene' is required")
                case CommandActionEnum.SHOW_FILTER:
                    if not data.get("source"):
                        raise ValueError("'source' is required")
                    if not data.get("filter"):
                        raise ValueError("'filter' is required")

            mappings.append(MIDIMapping(**row))
            print(mappings[-1])

        self._mappings = mappings

    # https://spotlightkid.github.io/python-rtmidi/rtmidi.html#rtmidi.MidiIn.set_callback
    def __call__(self, event: tuple, data: object = None) -> None:
        try:
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

                msg_channel = msg.channel + 1

                # Raw MIDI channel is 0-based
                if msg_channel != channel:
                    continue

                if msg.value != mapping.value:
                    continue

                command: Command

                match CommandActionEnum(mapping.action):
                    case CommandActionEnum.SWITCH_SCENE:
                        command = SwitchSceneCommand(**mapping.data)
                    case CommandActionEnum.SHOW_FILTER:
                        command = ShowFilterCommand(**mapping.data)

                self._q.put(command)
                break
        except Exception as exc:
            print("[MIDI] ERROR:", exc)
            raise


def _listen_midi(
    port: str | None,
    q: queue.Queue,
    ready_event: threading.Event,
    close_event: threading.Event,
) -> None:
    print(f"Selected port: {port}")

    try:
        midiin, port_name = open_midiinput(
            port,
            client_name="python-obs-midi",
            port_name="MIDI Input",
        )

        config = json.loads(pathlib.Path("config.json").read_text())

        midiin.set_callback(MIDIInputHandler(port_name, config, q))

        with midiin:
            print("[MIDI] Listening for messages...")
            ready_event.set()

            try:
                while not close_event.is_set():
                    time.sleep(0.2)
                print("[MIDI] Stopped")
            except KeyboardInterrupt:
                print("[MIDI] Closing...")

    except Exception as exc:
        print("[MIDI] ERROR:", exc)
        ready_event.set()
        raise


def start_midi_in_thread(
    port: str | None, q: queue.Queue, close_event: threading.Event
) -> threading.Thread:
    ready_event = threading.Event()
    thread = threading.Thread(
        target=_listen_midi, args=(port, q, ready_event, close_event)
    )
    thread.daemon = True
    thread.start()

    try:
        ready_event.wait()
    except KeyboardInterrupt:
        pass

    return thread
