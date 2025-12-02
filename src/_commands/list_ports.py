import rtmidi


def list_ports() -> None:
    with rtmidi.MidiOut() as midiout:
        ports = midiout.get_ports()
        for port in ports:
            print(port)
