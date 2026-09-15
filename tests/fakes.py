# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test doubles shared by the process tests."""

import signal


class FakeProcessTable:
    """Stands in for os.kill, so no real process is started or signalled."""

    def __init__(self) -> None:
        self.alive: set[int] = set()
        self.signals: list[tuple[int, int]] = []

    def kill(self, pid: int, sig: int) -> None:
        if pid not in self.alive:
            raise ProcessLookupError(pid)
        self.signals.append((pid, sig))
        if sig == signal.SIGINT:
            self.alive.discard(pid)
