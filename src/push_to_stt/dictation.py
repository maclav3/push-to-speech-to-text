# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
"""Record the microphone, transcribe the audio, and type the text."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from . import DictationError, missing_program
from .background import BackgroundProcess
from .config import SAMPLE_RATE, Settings


class Recorder:
    """The arecord process that captures one dictation."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.process = BackgroundProcess(settings.pid_file)

    @property
    def is_recording(self) -> bool:
        return self.process.is_running

    def start(self) -> None:
        if self.is_recording:
            raise DictationError("Already recording.")
        self.settings.wav_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings.wav_file.unlink(missing_ok=True)
        self.process.start(self._arecord_command())

    def stop(self) -> Path:
        """End the recording and return the path of the WAV file."""
        if not self.process.stop():
            raise DictationError("Not recording.")
        wav = self.settings.wav_file
        if not wav.exists() or wav.stat().st_size == 0:
            raise DictationError("No audio was recorded.")
        return wav

    def cancel(self) -> None:
        self.process.stop()
        self.settings.wav_file.unlink(missing_ok=True)

    def _arecord_command(self) -> list[str]:
        command = ["arecord", "--quiet"]
        if self.settings.audio_device:
            command += ["--device", self.settings.audio_device]
        # Whisper wants 16 kHz mono, so record that and skip a conversion step.
        command += ["--format", "S16_LE"]
        command += ["--rate", str(SAMPLE_RATE)]
        command += ["--channels", "1"]
        command += ["--file-type", "wav"]
        command.append(str(self.settings.wav_file))
        return command


def load_model(settings: Settings):
    """Load Whisper. This costs about a second, so callers reuse the result."""
    # The import pulls in ctranslate2 and costs about a second, so it waits here
    # instead of at start-up, where it would delay the recording.
    import faster_whisper

    try:
        return faster_whisper.WhisperModel(
            settings.model,
            device="cpu",
            compute_type="int8",
            cpu_threads=os.cpu_count(),
        )
    except Exception as error:
        # A download failure or a bad model name would otherwise kill the worker
        # in silence, because its output goes nowhere.
        raise DictationError(
            f"Cannot load the {settings.model} model: {error}"
        ) from error


def transcribe(wav: Path, settings: Settings, model=None) -> str:
    """Turn the recording into text. Returns an empty string for silence."""
    if model is None:
        model = load_model(settings)
    segments, _info = model.transcribe(
        str(wav),
        language=settings.language,
        # The voice filter drops silence, which otherwise makes Whisper invent words.
        vad_filter=True,
        # One candidate instead of five. The extra four rarely change the words.
        beam_size=1,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


def type_text(text: str) -> None:
    """Type the text into whichever field has focus."""
    try:
        # Reading from stdin keeps text that starts with a dash out of the parser.
        result = subprocess.run(
            ["ydotool", "type", "--file", "-"], input=text, text=True, check=False
        )
    except FileNotFoundError:
        raise missing_program("ydotool") from None
    if result.returncode != 0:
        raise DictationError(
            "ydotool cannot type. Check /dev/uinput access with: push-to-stt setup"
        )
