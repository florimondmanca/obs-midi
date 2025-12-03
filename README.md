# obs-midi-python

A bridge to OBS using MIDI via obs-websocket.

## Requirements

* Python 3.12+
* Make

## Usage

Install: `make install`

Configure: edit the generated `.env` file with the following variables:

* `OBS_PORT`: port of the obs-websockets server (default: 4455)
* `OBS_PASSWORD` (**required**): password for the obs-websockets server
* `MIDI_PORT`: the MIDI port to listen on, for example `20:0`. Leave empty or unset to be prompted with a list of options upon running the program. Show available ports using `make input_ports`.

Run: `make run`

## License

MIT
