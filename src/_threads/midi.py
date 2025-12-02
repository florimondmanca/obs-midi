import queue
import threading
import time

import mido
from rtmidi.midiutil import open_midiinput

from .._models.command import (
    SwitchSceneCommand,
)
from .._models.midi import MIDITriggerRepository


class MIDIInputHandler:
    # https://github.com/SpotlightKid/python-rtmidi/blob/master/examples/midi2command/midi2command.py

    def __init__(
        self, port_name: str, trigger_repository: MIDITriggerRepository, q: queue.Queue
    ) -> None:
        self._port_name = port_name
        self._trigger_repository = trigger_repository
        self._q = q

    # https://spotlightkid.github.io/python-rtmidi/rtmidi.html#rtmidi.MidiIn.set_callback
    def __call__(self, event: tuple, data: object = None) -> None:
        try:
            msg_bytes, _ = event

            msg: mido.Message = mido.parse(msg_bytes)
            print(f"[MIDI] Msg: {msg}")

            scene = self._trigger_repository.match_scene(msg)

            if scene is not None:
                self._q.put(SwitchSceneCommand(scene=scene))
        except Exception as exc:
            print("[MIDI] ERROR:", exc)
            raise


def _listen_midi(
    port: str | None,
    trigger_repository: MIDITriggerRepository,
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

        midiin.set_callback(MIDIInputHandler(port_name, trigger_repository, q))

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
    port: str | None,
    trigger_repository: MIDITriggerRepository,
    q: queue.Queue,
    close_event: threading.Event,
) -> threading.Thread:
    ready_event = threading.Event()
    thread = threading.Thread(
        target=_listen_midi,
        args=(port, trigger_repository, q, ready_event, close_event),
    )
    thread.daemon = True
    thread.start()

    try:
        ready_event.wait()
    except KeyboardInterrupt:
        pass

    return thread
