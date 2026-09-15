# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure how loud a recording is right now, and draw it as blocks.

The reading comes from the end of the file the recorder is still writing. No
second capture stream is needed, so the meter cannot disturb the recording.
"""

from __future__ import annotations

import array
import math
from collections.abc import Sequence
from pathlib import Path

BLOCKS = "▁▂▃▄▅▆▇█"
BAR_WIDTH = 12

HEADER_BYTES = 44
WINDOW_BYTES = 4096
SAMPLE_PEAK = 32768
FLOOR_DB = -50.0


def tail_loudness(wav: Path, window_bytes: int = WINDOW_BYTES) -> float:
    """Loudness of the last fragment of the recording, from 0.0 to 1.0."""
    try:
        size = wav.stat().st_size
    except OSError:
        return 0.0
    start = max(HEADER_BYTES, size - window_bytes)
    # Keep the window on a sample boundary, or the audio reads as noise.
    start -= (start - HEADER_BYTES) % 2
    if size - start < 2:
        return 0.0
    with wav.open("rb") as recording:
        recording.seek(start)
        data = recording.read(size - start)

    samples = array.array("h")
    samples.frombytes(data[: len(data) - len(data) % 2])
    return _loudness(samples)


def bar(levels: Sequence[float]) -> str:
    """Draw the recent levels as one row of blocks, newest on the right."""
    recent = list(levels)[-BAR_WIDTH:]
    padded = [0.0] * (BAR_WIDTH - len(recent)) + recent
    return "".join(
        BLOCKS[min(len(BLOCKS) - 1, int(level * len(BLOCKS)))] for level in padded
    )


def _loudness(samples: array.array) -> float:
    if not samples:
        return 0.0
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    rms = math.sqrt(mean_square) / SAMPLE_PEAK
    if rms <= 0.0:
        return 0.0
    # Ears hear loudness on a log scale, so a linear bar would barely move.
    decibels = 20 * math.log10(rms)
    return min(1.0, max(0.0, (decibels - FLOOR_DB) / -FLOOR_DB))
