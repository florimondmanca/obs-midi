# python-obs-midi

A bridge to control [OBS](https://obsproject.com/) using MIDI, powered by OBS' native [WebSocket Remote Control](https://obsproject.com/kb/remote-control-guide).

## Why?

As of December 2025, OBS does not have native MIDI control.

The most popular option is the [obs-midi-mg](https://github.com/nhielost/obs-midi-mg) plugin.

But maintenance has stalled and I was not able to make it work on latest OBS versions (v31+).

Besides, in my setup running this plugin eats up a lot of CPU. This appears to be due to inefficient MIDI polling performed by `libremidi`.

`python-obs-midi` relies on the native WebSocket remote control capability of OBS (which should be more future-proof), and on `python-rtmidi`, a well-established and performant MIDI library for Python.

## Disclaimer

I develop this software for my own use, which is using OBS as a video clip playback solution for live music gigs.

There is no maintenance intended, but I would be happy for this code to be reused and tweaked by others.

## Features

- Cross-platform (hopefully so, but developed primarily on Linux Mint).
- Supports scene switching and filter toggling.
- Define MIDI triggers directly in scene or filter names, making the configuration visible and always in-sync with your OBS session.

Limitations:

- Requires a working Python environment to run.
- Only MIDI CC is supported for now.
- GUI is very basic.

## Requirements

* Python 3.12+ with dev tools (pip, venv, etc)
* Tcl/Tk and Tkinter: check with `python3 -m tkinter`. If this fails:
  * On macOS, run `brew install python-tk` to install tcl-tk and tkinter into the system Python3.

## Installation

Download a copy of the source code, either via git by cloning this repo, or by downloading the ZIP archive.

Then open a terminal at the root of the source code folder, and run `make install`.

## Configuration

Launch OBS, then enable and configure the WebSocket server. See [official docs](https://obsproject.com/kb/remote-control-guide) for more info.

## Usage

### Configuring MIDI triggers

`python-obs-midi` reads MIDI triggers directly from scene and filter names. This ensures the MIDI configuration is always in sync and visible in your OBS session.

For MIDI CC, the format should be:

```
<name> :: CCnn#vv@ch
```

where `nn` is the CC number, `vv` the CC value, and `ch` the MIDI channel.

For example, if a scene is named:

```
Home screen :: CC20#127@3
```

then receiving MIDI CC 20 with value 127 on channel 3 will make OBS switch to the "Home screen" scene.

### Running via the GUI (recommended)

Plug your MIDI interface into your computer

Then open a terminal at the root of the source code folder, and run: `make run`

Select the MIDI port to use, enter the configured OBS WebSocket port and password, then click "Start".

### Running via the command line interface (CLI) (Advanced)

The program may also be run from the terminal via a traditional CLI.

```bash
venv/bin/python main.py --midi-port=[MIDI_PORT] --obs-port=4455 --obs-password=[OBS_PASSWORD]
```

The program can also read all options from environment variables:

* `OBS_PORT`: port of the obs-websockets server (default: 4455)
* `OBS_PASSWORD`: set here the password of the OBS WebSocket server
* `MIDI_PORT`: the MIDI port to listen on, for example `20:0`. Leave empty or unset to be prompted with a list of options upon running the program. Show available ports using `make input_ports`.

For convenience, you can define these environment variables in a local `.env` file and run `make cli`, which will automatically load the dotenv file.

## Development

Install additional development dependencies using `make install_dev`.

See the `Makefile` for additional development commands such as `format` and `check`.

OBS has native WebSocket support. Its [protocol](github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md) provides an extended set of operations for controlling an OBS session.

As such, I hope building MIDI control on top of this native WebSocket capability should be fairly future-proof.

## License

MIT
