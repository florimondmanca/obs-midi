import rtmidi


def get_midi_ports() -> list[str]:
    with rtmidi.MidiOut() as midiout:
        return midiout.get_ports()
