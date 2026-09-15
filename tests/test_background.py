# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
import signal
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from push_to_stt import DictationError
from push_to_stt.background import BackgroundProcess

from .fakes import FakeProcessTable

PID = 4242


class BackgroundProcessTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(mock.patch.stopall)
        self.pid_file = Path(directory.name) / "state" / "thing.pid"
        self.process = BackgroundProcess(self.pid_file)

        self.table = FakeProcessTable()
        mock.patch("push_to_stt.background.os.kill", self.table.kill).start()
        self.popen = mock.patch(
            "push_to_stt.background.subprocess.Popen", side_effect=self.fake_popen
        ).start()

    def fake_popen(self, command, **kwargs):
        self.table.alive.add(PID)
        return mock.Mock(pid=PID)

    def test_start_creates_the_state_directory_and_the_pid_file(self):
        self.process.start(["sleep", "30"])
        self.assertEqual(self.pid_file.read_text(), str(PID))
        self.assertTrue(self.process.is_running)

    def test_the_child_is_detached_from_our_pipes(self):
        """A caller that reads our output must not wait for the child to finish."""
        self.process.start(["sleep", "30"])
        self.assertTrue(self.popen.call_args.kwargs["start_new_session"])
        self.assertIsNotNone(self.popen.call_args.kwargs["stdout"])

    def test_a_missing_program_names_it(self):
        self.popen.side_effect = FileNotFoundError
        with self.assertRaises(DictationError) as caught:
            self.process.start(["nosuchprogram"])
        self.assertIn("nosuchprogram", str(caught.exception))

    def test_stop_interrupts_the_process_and_clears_the_pid_file(self):
        self.process.start(["sleep", "30"])
        self.assertTrue(self.process.stop())
        self.assertEqual(self.table.signals[-1], (PID, signal.SIGINT))
        self.assertFalse(self.pid_file.exists())
        self.assertFalse(self.process.is_running)

    def test_stop_reports_that_nothing_was_running(self):
        self.assertFalse(self.process.stop())

    def test_a_stale_pid_file_does_not_count_as_running(self):
        self.pid_file.parent.mkdir(parents=True)
        self.pid_file.write_text("999999")
        self.assertFalse(self.process.is_running)
        self.assertFalse(self.pid_file.exists())

    def test_a_damaged_pid_file_does_not_count_as_running(self):
        self.pid_file.parent.mkdir(parents=True)
        self.pid_file.write_text("not a number")
        self.assertFalse(self.process.is_running)


if __name__ == "__main__":
    unittest.main()
