# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from push_to_stt import DictationError
from push_to_stt.cli import main


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
        self.recorder.stop.return_value = Path(directory.name) / "take.wav"
        self.recorder.stop.return_value.write_bytes(b"RIFF fake wav")
        self.transcribe = mock.patch(
            "push_to_stt.cli.transcribe", return_value="hello world"
        ).start()
        self.type_text = mock.patch("push_to_stt.cli.type_text").start()
        self.meter = mock.patch("push_to_stt.cli.meter").start()

    def test_toggle_starts_when_nothing_is_recording(self):
        self.assertEqual(main(["toggle"]), 0)
        self.recorder.start.assert_called_once()
        self.type_text.assert_not_called()

    def test_toggle_stops_and_types_when_recording(self):
        self.recorder.is_recording = True
        self.assertEqual(main(["toggle"]), 0)
        self.recorder.stop.assert_called_once()
        self.type_text.assert_called_once_with("hello world")

    def test_no_command_means_toggle(self):
        self.assertEqual(main([]), 0)
        self.recorder.start.assert_called_once()

    def test_silence_types_nothing(self):
        self.transcribe.return_value = ""
        self.assertEqual(main(["stop"]), 0)
        self.type_text.assert_not_called()

    def test_the_recording_is_deleted_even_when_whisper_fails(self):
        self.transcribe.side_effect = DictationError("engine broke")
        self.assertEqual(main(["stop"]), 1)
        self.assertFalse(self.recorder.stop.return_value.exists())

    def test_a_failure_reports_exit_code_one(self):
        self.recorder.start.side_effect = DictationError("already recording")
        self.assertEqual(main(["start"]), 1)

    def test_cancel_reaches_the_recorder(self):
        self.assertEqual(main(["cancel"]), 0)
        self.recorder.cancel.assert_called_once()

    def test_setup_grants_access_then_binds_the_hotkey(self):
        with (
            mock.patch("push_to_stt.cli.grant_uinput_access") as grant,
            mock.patch("push_to_stt.cli.bind_hotkey") as bind,
        ):
            self.assertEqual(main(["setup", "--hotkey", "<Super>x"]), 0)
        grant.assert_called_once()
        bind.assert_called_once_with("<Super>x")


class MeterTest(unittest.TestCase):
    """The level meter runs beside the recorder and must never outlive it."""

    def setUp(self) -> None:
        CliTest.setUp(self)

    def test_start_puts_the_meter_on_screen(self):
        main(["start"])
        self.meter.spawn.assert_called_once()

    def test_stop_takes_the_meter_down(self):
        self.recorder.is_recording = True
        main(["stop"])
        self.meter.stop.assert_called_once()

    def test_the_meter_goes_before_the_text_is_typed(self):
        """Whisper takes seconds, so the meter must not sit there during it."""
        order = []
        self.meter.stop.side_effect = lambda *_: order.append("meter")
        self.transcribe.side_effect = lambda *_: order.append("transcribe") or "hello"
        main(["stop"])
        self.assertEqual(order, ["meter", "transcribe"])

    def test_cancel_takes_the_meter_down(self):
        main(["cancel"])
        self.meter.stop.assert_called_once()

    def test_a_failed_recording_still_takes_the_meter_down(self):
        self.recorder.stop.side_effect = DictationError("No audio was recorded.")
        self.assertEqual(main(["stop"]), 1)
        self.meter.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
