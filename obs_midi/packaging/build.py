import platform
import subprocess
from pathlib import Path
from typing import Literal

name = "obs-midi"
dist_path = Path("dist") / name
icon_path = Path("assets") / "obs-midi.icns"
linux_executable_dest_path = Path.home() / ".local" / "bin" / "obs-midi"
linux_desktop_file_dest_dir = Path.home() / ".local" / "share" / "applications"
linux_desktop_file_path_src = Path("assets") / "linux" / "obs-midi.desktop"
linux_icon_file_path_src = Path("assets") / "linux" / "obs-midi-256x256.png"

assert linux_desktop_file_path_src.exists()
assert linux_icon_file_path_src.exists()


def _check_subprocess(result: subprocess.CompletedProcess) -> None:
    if result.returncode:
        raise SystemExit(result.returncode)


def _ask(question: str, prefer: Literal["y", "n"]) -> bool:
    try:
        answer = input(
            f"{question} ({'Y' if prefer == 'y' else 'y'}/{'N' if prefer == 'n' else 'n'}) "
        )
    except KeyboardInterrupt:
        return False

    match prefer:
        case "y":
            return not bool(answer) or answer.lower() == "y"
        case "n":
            return not bool(answer) or answer.lower() != "n"


def _ask_and_install_on_linux() -> None:
    if platform.system() != "Linux":
        return

    if not _ask(f"Install executable to {linux_executable_dest_path}?", prefer="y"):
        return

    _check_subprocess(
        subprocess.run(["sudo", "cp", str(dist_path), str(linux_executable_dest_path)])
    )
    print(f"SUCCESS: Executable copied to {linux_executable_dest_path}")

    if not _ask("Install desktop entry?", prefer="y"):
        return

    _check_subprocess(
        subprocess.run(
            ["xdg-icon-resource", "install", "--size", "256", linux_icon_file_path_src]
        )
    )

    _check_subprocess(
        subprocess.run(["desktop-file-validate", linux_desktop_file_path_src])
    )

    _check_subprocess(
        subprocess.run(
            [
                "desktop-file-install",
                "--dir",
                linux_desktop_file_dest_dir,
                linux_desktop_file_path_src,
            ]
        )
    )

    print("SUCCESS: Desktop entry created")


def build() -> None:
    PYINSTALLER_COMMAND: list[str] = [
        "venv/bin/pyinstaller",
        "main.py",
        "--onefile",
        "--name",
        name,
        "--icon",
        str(icon_path),  # Windows or macOS only
    ]

    result = subprocess.run(PYINSTALLER_COMMAND)

    if result.returncode:
        raise SystemExit(result.returncode)

    print()
    assert dist_path.exists()
    print(f"SUCCESS: Executable built at: {dist_path}")

    _ask_and_install_on_linux()


if __name__ == "__main__":
    build()
