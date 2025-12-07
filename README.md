# OBS MIDI

A bridge to control [OBS](https://obsproject.com/) using MIDI, powered by the native [WebSocket Remote Control](https://obsproject.com/kb/remote-control-guide) capabilities of OBS.

## Why?

As of December 2025, OBS does not have native MIDI control.

The most popular option is the [obs-midi-mg](https://github.com/nhielost/obs-midi-mg) plugin, but it has issues with latest OBS versions and tends to eat up a lot of CPU while listening for MIDI messages.

Instead, OBS MIDI relies on the native WebSocket remote control capability of OBS and the well-establiedh `python-rtmidi` library, which should make for a future-proof solution.

## Disclaimer

There is no maintenance intended, but I would be happy for this code to be reused and tweaked by others.

I initially developed this software for my own use, i.e. using OBS as a video clip playback solution for live music gigs.

## Features

- Nice and simple GUI program
- Cross-platform (although primarily tested on Linux Mint)
- Actions: scene switching, filter toggling
- WYSIWYG configuration: define MIDI triggers directly in scene or filter names.

Limitations:

- Requires a working Python environment to package from source.
- Only MIDI CC can be used as triggers, for now.

## Requirements

* Python 3.12+ with dev tools (pip, venv, etc)
* Tcl/Tk and Tkinter: check with `python3 -m tkinter`. If this fails:
  * On macOS, run `brew install python-tk` to install tcl-tk and tkinter into the system Python3.

## Installation

1. Download a copy of the source code, either via git by cloning this repo, or by downloading the ZIP archive.
2. Open a terminal at the root of the source code directory.
3. Run `make` to install dependencies and build the executable file.
  * On Linux: this will also ask to install and create a desktop entry. You can then find the "OBS MIDI" program in the desktop menu, as well as the `obs-midi` command in the terminal.
  * For other operating systems: this will create the executable program at `dist/obs-midi`. It can be run by double-clicking on it, and you can place it wherever you'd like on your computer.

## Usage

## Configuring OBS

Launch OBS, then enable and configure the WebSocket server -- mainly setting the port and password.

See [official docs](https://obsproject.com/kb/remote-control-guide) for more info.

### Configuring MIDI triggers

OBS MIDI reads MIDI triggers directly from scene and filter names. This ensures the MIDI configuration is always in sync and visible in your OBS session.

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

Then start the "OBS MIDI" program (Linux) or (for all operating systems) the compiled `obs-midi` program.

Select the MIDI port to use, enter the configured OBS WebSocket port and password, then click "Start".

### Running via the command line interface (CLI) (Advanced)

_**TODO**: this section is obsolete._

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

## License

MIT
