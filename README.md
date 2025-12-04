# python-obs-midi

A bridge to control [OBS](https://obsproject.com/) using MIDI via [OBS WebSocket](https://obsproject.com/kb/remote-control-guide).

## Disclaimer

I develop this software for my own use, which is using OBS as a video clip playback solution for live music gigs.

There is no maintenance intended, but I would be happy for this code to be reused and tweaked by others.

## Features

- Supports scene switching and filter toggling.
- MIDI triggers are defined directly in OBS, as part of scene or filter names.

Limitations:

- Only MIDI CC is supported for now.
- No GUI (yet).
- Requires a working Python environment to run.

## Requirements

* Python 3.12+ with dev tools (pip, venv, etc)
* `make`, for convenience

## Usage

First, launch OBS, and enable and configure the WebSocket server. See [official docs](https://obsproject.com/kb/remote-control-guide) for more info.

You must now install this software:

* Download the source code, either via git by cloning this repo, or download the ZIP archive.
* Open a terminal and run `make install`.

A `.env` file will be generated with the following variables:

* `OBS_PORT`: port of the obs-websockets server (default: 4455)
* `OBS_PASSWORD` (**required**): set here the password of the OBS WebSocket server
* `MIDI_PORT`: the MIDI port to listen on, for example `20:0`. Leave empty or unset to be prompted with a list of options upon running the program. Show available ports using `make input_ports`.

Run: `make run`

## Development

Install additional development dependencies using `make install_dev`.

See the `Makefile` for additional development commands such as `format` and `check`.

## Why?

As of December 2025, OBS does not have native MIDI control. It seems the only semi-viable option is the [obs-midi-mg](https://github.com/nhielost/obs-midi-mg) plugin. But it has now become unmaintained and does not work (as per my testing) on latest OBS versions.

OBS has native WebSocket support. Its [protocol](github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md) provides an extended set of operations for controlling an OBS session.

As such, I hope building MIDI control on top of this native WebSocket capability should be fairly future-proof.

## License

MIT
