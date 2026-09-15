# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
"""A process that outlives the command which started it.

One hotkey press starts a process and the next press arrives in a different
process. A PID file on disk is the only handover between the two.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from . import missing_program

STOP_TIMEOUT = 5.0


class BackgroundProcess:
    def __init__(self, pid_file: Path) -> None:
        self.pid_file = pid_file

    @property
    def pid(self) -> int | None:
        """The running process, or None. A stale PID file counts as None."""
        try:
            pid = int(self.pid_file.read_text())
        except (OSError, ValueError):
            return None
        if not _alive(pid):
            self.pid_file.unlink(missing_ok=True)
            return None
        return pid

    @property
    def is_running(self) -> bool:
        return self.pid is not None

    def start(self, command: list[str]) -> None:
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            process = subprocess.Popen(
                command,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            raise missing_program(command[0]) from None
        self.pid_file.write_text(str(process.pid))

    def stop(self, timeout: float = STOP_TIMEOUT) -> bool:
        """Interrupt the process. Returns False if it was not running."""
        pid = self.pid
        if pid is None:
            return False
        # SIGINT lets the process finish its work. SIGKILL would not.
        os.kill(pid, signal.SIGINT)
        _wait_for_exit(pid, timeout)
        self.pid_file.unlink(missing_ok=True)
        return True


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _wait_for_exit(pid: int, timeout: float) -> None:
    """Wait for a process that is not our child, so os.wait cannot be used."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _alive(pid):
            return
        time.sleep(0.05)
