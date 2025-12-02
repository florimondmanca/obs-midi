import argparse

from ._commands.list_ports import list_ports
from ._commands.run import run


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_list_ports = subparsers.add_parser("list", help="List MIDI ports")
    parser_list_ports.set_defaults(func=lambda args: list_ports())

    parser_listen = subparsers.add_parser("run", help="Run MIDI / obs-websocket bridge")
    parser_listen.add_argument("-p", "--midi-port", help="MIDI port")
    parser_listen.add_argument("--obs-port", help="obs-websocket port", default=4455)
    parser_listen.add_argument("--obs-password", help="obs-websocket password")
    parser_listen.set_defaults(
        func=lambda args: run(
            midi_port=args.midi_port,
            obs_port=args.obs_port,
            obs_password=args.obs_password,
        )
    )

    args = parser.parse_args()

    try:
        func = args.func
    except AttributeError:
        parser.print_help()
        raise SystemExit(1)

    func(args)
