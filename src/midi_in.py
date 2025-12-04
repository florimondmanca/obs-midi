import threading
import time

import mido
from rtmidi.midiutil import open_midiinput

from .app import App


class MIDInputThread(threading.Thread):
    def __init__(
        self,
        *,
        port: str | None,
        app: App,
        midi_ready_event: threading.Event,
        close_event: threading.Event,
    ) -> None:
        super().__init__()
        self._port = port
        self._app = app
        self._midi_ready_event = midi_ready_event
        self._close_event = close_event

    def run(
        self,
    ) -> None:
        print(f"Selected port: {self._port}")

        try:
            midi_input, port_name = open_midiinput(
                self._port,
                use_virtual=False,
                client_name="python-obs-midi",
                port_name="Midi In",
            )

            # https://spotlightkid.github.io/python-rtmidi/rtmidi.html#rtmidi.MidiIn.set_callback
            @midi_input.set_callback
            def midi_callback(event: tuple, data: object = None) -> None:
                try:
                    msg_bytes, _ = event
                    msg: mido.Message = mido.parse(msg_bytes)
                    print(f"[MIDI] Msg: {msg}")
                    self._app.on_midi_message(msg)
                except Exception as exc:
                    print("[MIDI] ERROR:", exc)
                    raise

            with midi_input:
                print("[MIDI] Listening for messages...")
                self._midi_ready_event.set()

                try:
                    while not self._close_event.is_set():
                        time.sleep(0.2)
                    print("[MIDI] Stopped")
                except KeyboardInterrupt:
                    print("[MIDI] Closing...")

        except Exception as exc:
            print("[MIDI] ERROR:", exc)
            self._midi_ready_event.set()
            self._close_event.set()
            raise
