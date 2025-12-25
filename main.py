from obs_midi.gui.main import run_gui
from obs_midi.utils.pyinstaller import pyinstaller_hints

pyinstaller_hints()

if __name__ == "__main__":
    run_gui()
