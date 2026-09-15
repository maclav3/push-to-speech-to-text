# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line interface. The hotkey runs `push-to-stt toggle`."""

from __future__ import annotations

import argparse
import sys
from argparse import Namespace

from . import DictationError
from .config import Settings
from .desktop import DEFAULT_HOTKEY, bind_hotkey, grant_uinput_access, notify
from .dictation import Recorder, transcribe, type_text


def start(args: Namespace, settings: Settings) -> None:
    """Start recording."""
    Recorder(settings).start()
    notify("Recording", "Press the hotkey again to transcribe.")


def stop(args: Namespace, settings: Settings) -> None:
    """Stop recording, then transcribe and type the text."""
    wav = Recorder(settings).stop()
    notify("Transcribing", f"Model: {settings.model}")
    try:
        text = transcribe(wav, settings)
    finally:
        wav.unlink(missing_ok=True)
    if not text:
        notify("Nothing heard", "The recording held no speech.")
        return
    type_text(text)
    notify("Typed", text)


def cancel(args: Namespace, settings: Settings) -> None:
    """Stop recording and throw the audio away."""
    Recorder(settings).cancel()
    notify("Dictation cancelled")


def toggle(args: Namespace, settings: Settings) -> None:
    """Start recording, or stop and type the text."""
    if Recorder(settings).is_recording:
        stop(args, settings)
    else:
        start(args, settings)


def setup(args: Namespace, settings: Settings) -> None:
    """Grant /dev/uinput access and bind the hotkey."""
    grant_uinput_access()
    bind_hotkey(args.hotkey)
    print(f"\nReady. Press {args.hotkey} to record. Press it again to type the text.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="push-to-stt", description=__doc__)
    parser.set_defaults(run=toggle)
    commands = parser.add_subparsers()
    for action in (toggle, start, stop, cancel):
        commands.add_parser(action.__name__, help=action.__doc__).set_defaults(
            run=action
        )
    setup_parser = commands.add_parser(
        "setup", help="Grant access and bind the hotkey."
    )
    setup_parser.add_argument("--hotkey", default=DEFAULT_HOTKEY)
    setup_parser.set_defaults(run=setup)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.run(args, Settings.from_env())
    except DictationError as error:
        notify("Dictation failed", str(error))
        print(f"push-to-stt: {error}", file=sys.stderr)
        return 1
    return 0
