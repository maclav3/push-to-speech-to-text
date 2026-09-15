"""Hotkey dictation for Linux.

The package drives three outside programs: arecord for the microphone, ydotool
for the keyboard, and gsettings for the GNOME hotkey. Whisper runs in process.
"""

__version__ = "0.1.0"

INSTALL_HINTS = {
    "arecord": "Install it with: sudo apt install alsa-utils",
    "ydotool": "Install it with: sudo apt install ydotool",
    "gsettings": "It comes with GNOME. Bind the hotkey by hand instead.",
}


class DictationError(Exception):
    """An error worth showing to the user as a desktop notification."""


def missing_program(name: str) -> DictationError:
    """Build the error for a program that is not installed."""
    hint = INSTALL_HINTS.get(name, "")
    return DictationError(f"{name} is not installed. {hint}".strip())
