# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
"""The worker that lives for one dictation.

It draws the level while you speak, then transcribes and types what you said.
Doing the work here, rather than in the command that ends the recording, means
the hotkey never waits for Whisper.
"""

from __future__ import annotations

import sys
import time
from collections import deque

from .background import BackgroundProcess
from .config import Settings
from .desktop import close_notification, notify, notify_progress
from .dictation import transcribe, type_text
from .meter import BAR_WIDTH, bar, tail_loudness

REDRAW_SECONDS = 0.12


def spawn(settings: Settings) -> None:
    """Start the worker beside the recorder, in its own process."""
    BackgroundProcess(settings.session_pid_file).start(
        [sys.executable, "-m", "push_to_stt", "session"],
        # onnxruntime drops a telemetry file into the current directory, so the
        # worker runs from our own directory rather than wherever you were.
        cwd=settings.state_dir,
    )


def finish(settings: Settings) -> None:
    """Tell the worker the recording is over, without waiting for its work."""
    BackgroundProcess(settings.session_pid_file).stop(timeout=0.0)


def run(settings: Settings, interval: float = REDRAW_SECONDS) -> None:
    """Draw the level until interrupted, then write out what was said."""
    notification = notify_progress("Recording", bar([]))
    try:
        _draw(settings, notification, interval)
    except KeyboardInterrupt:
        pass
    finally:
        close_notification(notification)
    _write_out(settings)


def _draw(settings: Settings, notification: int, interval: float) -> None:
    history: deque[float] = deque([0.0] * BAR_WIDTH, maxlen=BAR_WIDTH)
    while True:
        history.append(tail_loudness(settings.wav_file))
        notify_progress("Recording", bar(history), replace_id=notification)
        time.sleep(interval)


def _write_out(settings: Settings) -> None:
    wav = settings.wav_file
    # A cancelled dictation deletes the recording, which leaves nothing to do.
    if not wav.exists() or wav.stat().st_size == 0:
        return
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
