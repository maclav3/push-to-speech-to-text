# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line interface. The hotkey runs `push-to-stt toggle`."""

from __future__ import annotations

import argparse
import sys
from argparse import Namespace

from . import DictationError, session
from .config import Settings
from .desktop import DEFAULT_HOTKEY, bind_hotkey, grant_uinput_access, notify
from .dictation import Recorder


def start(args: Namespace, settings: Settings) -> None:
    """Start recording."""
    Recorder(settings).start()
    # The worker is the recording indicator, so no separate popup is needed.
    session.spawn(settings)


def stop(args: Namespace, settings: Settings) -> None:
    """Stop recording. The worker transcribes and types what you said."""
    try:
        Recorder(settings).stop()
    finally:
        session.finish(settings)


def cancel(args: Namespace, settings: Settings) -> None:
    """Stop recording and throw the audio away."""
    # Deleting the recording first leaves the worker nothing to transcribe.
    Recorder(settings).cancel()
    session.finish(settings)
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


def run_session(args: Namespace, settings: Settings) -> None:
    """Draw the level, then transcribe and type. The start command runs this."""
    session.run(settings)


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
    # No help text, so argparse keeps this internal command out of the list.
    commands.add_parser("session").set_defaults(run=run_session)
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
