# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
"""Settings, read once from the environment.

A GNOME hotkey starts the tool with an empty shell environment. Put overrides in
~/.config/environment.d/ so that the desktop session exports them.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "small"
SAMPLE_RATE = 16000


@dataclass(frozen=True)
class Settings:
    state_dir: Path
    model: str = DEFAULT_MODEL
    language: str | None = None
    audio_device: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        runtime_dir = env.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
        return cls(
            state_dir=Path(runtime_dir) / "push-to-stt",
            model=env.get("STT_MODEL") or DEFAULT_MODEL,
            language=env.get("STT_LANGUAGE") or None,
            audio_device=env.get("STT_AUDIO_DEVICE") or None,
        )

    @property
    def pid_file(self) -> Path:
        return self.state_dir / "recorder.pid"

    @property
    def wav_file(self) -> Path:
        return self.state_dir / "take.wav"

    @property
    def meter_pid_file(self) -> Path:
        return self.state_dir / "meter.pid"
