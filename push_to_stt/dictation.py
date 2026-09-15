"""Record the microphone, transcribe the audio, and type the text."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from . import DictationError, missing_program
from .config import SAMPLE_RATE, Settings

STOP_TIMEOUT = 5.0


class Recorder:
    """A detached arecord process, tracked through a PID file.

    The process must outlive the command that starts it, because the next hotkey
    press arrives in a new process. The PID file is the handover between the two.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def pid(self) -> int | None:
        try:
            pid = int(self.settings.pid_file.read_text())
        except (OSError, ValueError):
            return None
        if not _process_alive(pid):
            self.settings.pid_file.unlink(missing_ok=True)
            return None
        return pid

    @property
    def is_recording(self) -> bool:
        return self.pid is not None

    def start(self) -> None:
        if self.is_recording:
            raise DictationError("Already recording.")
        self.settings.state_dir.mkdir(parents=True, exist_ok=True)
        self.settings.wav_file.unlink(missing_ok=True)
        try:
            process = subprocess.Popen(
                self._arecord_command(),
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            raise missing_program("arecord") from None
        self.settings.pid_file.write_text(str(process.pid))

    def stop(self) -> Path:
        """End the recording and return the path of the WAV file."""
        pid = self.pid
        if pid is None:
            raise DictationError("Not recording.")
        # SIGINT makes arecord write the final WAV header. SIGKILL would not.
        os.kill(pid, signal.SIGINT)
        _wait_for_exit(pid)
        self.settings.pid_file.unlink(missing_ok=True)
        wav = self.settings.wav_file
        if not wav.exists() or wav.stat().st_size == 0:
            raise DictationError("No audio was recorded.")
        return wav

    def cancel(self) -> None:
        pid = self.pid
        if pid is not None:
            os.kill(pid, signal.SIGINT)
            _wait_for_exit(pid)
            self.settings.pid_file.unlink(missing_ok=True)
        self.settings.wav_file.unlink(missing_ok=True)

    def _arecord_command(self) -> list[str]:
        command = ["arecord", "--quiet"]
        if self.settings.audio_device:
            command += ["--device", self.settings.audio_device]
        # Whisper wants 16 kHz mono, so record that and skip a conversion step.
        command += ["--format", "S16_LE", "--rate", str(SAMPLE_RATE),
                    "--channels", "1", "--file-type", "wav",
                    str(self.settings.wav_file)]
        return command


def transcribe(wav: Path, settings: Settings) -> str:
    """Turn the recording into text. Returns an empty string for silence."""
    # The import pulls in ctranslate2 and costs about a second, so it waits here
    # instead of at start-up, where it would delay the recording.
    from faster_whisper import WhisperModel

    model = WhisperModel(settings.model, device="cpu", compute_type="int8")
    # The voice filter drops silence, which otherwise makes Whisper invent words.
    segments, _info = model.transcribe(
        str(wav), language=settings.language, vad_filter=True
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


def type_text(text: str) -> None:
    """Type the text into whichever field has focus."""
    try:
        # Reading from stdin keeps text that starts with a dash out of the parser.
        result = subprocess.run(["ydotool", "type", "--file", "-"],
                                input=text, text=True, check=False)
    except FileNotFoundError:
        raise missing_program("ydotool") from None
    if result.returncode != 0:
        raise DictationError(
            "ydotool cannot type. Check /dev/uinput access with: push-to-stt setup"
        )


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _wait_for_exit(pid: int, timeout: float = STOP_TIMEOUT) -> None:
    """Wait for a process that is not our child, so os.wait cannot be used."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _process_alive(pid):
            return
        time.sleep(0.05)
