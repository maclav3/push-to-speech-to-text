# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
import io
import tempfile
import unittest
from unittest import mock

from push_to_stt import DictationError
from push_to_stt.cli import build_parser, main


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(mock.patch.stopall)
        mock.patch.dict("os.environ", {"XDG_RUNTIME_DIR": directory.name}).start()
        mock.patch("push_to_stt.cli.notify").start()
        for stream in ("stdout", "stderr"):
            mock.patch(f"sys.{stream}", new_callable=io.StringIO).start()

        self.recorder = mock.patch("push_to_stt.cli.Recorder").start().return_value
        self.recorder.is_recording = False
        self.session = mock.patch("push_to_stt.cli.session").start()

    def test_toggle_starts_when_nothing_is_recording(self):
        self.assertEqual(main(["toggle"]), 0)
        self.recorder.start.assert_called_once()
        self.recorder.stop.assert_not_called()

    def test_toggle_stops_when_recording(self):
        self.recorder.is_recording = True
        self.assertEqual(main(["toggle"]), 0)
        self.recorder.stop.assert_called_once()

    def test_no_command_means_toggle(self):
        self.assertEqual(main([]), 0)
        self.recorder.start.assert_called_once()

    def test_start_puts_the_worker_on_screen(self):
        main(["start"])
        self.session.spawn.assert_called_once()

    def test_stop_ends_the_recording_before_it_tells_the_worker(self):
        """The worker reads the file, so arecord must have closed it first."""
        order = []
        self.recorder.stop.side_effect = lambda: order.append("recorder")
        self.session.finish.side_effect = lambda *_: order.append("worker")
        main(["stop"])
        self.assertEqual(order, ["recorder", "worker"])

    def test_a_failed_recording_still_tells_the_worker(self):
        """Otherwise the meter would stay on screen for ever."""
        self.recorder.stop.side_effect = DictationError("No audio was recorded.")
        self.assertEqual(main(["stop"]), 1)
        self.session.finish.assert_called_once()

    def test_cancel_throws_the_recording_away_before_telling_the_worker(self):
        """The worker transcribes whatever it finds, so the file must go first."""
        order = []
        self.recorder.cancel.side_effect = lambda: order.append("recording deleted")
        self.session.finish.side_effect = lambda *_: order.append("worker")
        main(["cancel"])
        self.assertEqual(order, ["recording deleted", "worker"])

    def test_a_failure_reports_exit_code_one(self):
        self.recorder.start.side_effect = DictationError("already recording")
        self.assertEqual(main(["start"]), 1)

    def test_setup_grants_access_then_binds_the_hotkey(self):
        with (
            mock.patch("push_to_stt.cli.grant_uinput_access") as grant,
            mock.patch("push_to_stt.cli.bind_hotkey") as bind,
        ):
            self.assertEqual(main(["setup", "--hotkey", "<Super>x"]), 0)
        grant.assert_called_once()
        bind.assert_called_once_with("<Super>x")


class HelpTest(unittest.TestCase):
    def test_the_help_never_shows_argparse_internals(self):
        self.assertNotIn("SUPPRESS", build_parser().format_help())

    def test_the_internal_session_command_still_works(self):
        args = build_parser().parse_args(["session"])
        self.assertEqual(args.run.__name__, "run_session")


if __name__ == "__main__":
    unittest.main()
