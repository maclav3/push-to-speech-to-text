# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from push_to_stt.config import Settings
from push_to_stt.meter import BAR_WIDTH
from push_to_stt.session import run, spawn


class SessionRunTest(unittest.TestCase):
    """One worker draws the level, then types what was said."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(mock.patch.stopall)
        self.settings = Settings(state_dir=Path(directory.name))
        self.settings.state_dir.mkdir(parents=True, exist_ok=True)
        self.settings.wav_file.write_bytes(b"RIFF fake wav")

        self.notify = mock.patch(
            "push_to_stt.session.notify_progress", return_value=7
        ).start()
        self.close = mock.patch("push_to_stt.session.close_notification").start()
        mock.patch("push_to_stt.session.notify").start()
        mock.patch("push_to_stt.session.tail_loudness", return_value=0.5).start()
        # The draw loop only ends when the stop command interrupts it.
        mock.patch(
            "push_to_stt.session.time.sleep",
            side_effect=[None, None, KeyboardInterrupt],
        ).start()
        self.transcribe = mock.patch(
            "push_to_stt.session.transcribe", return_value="hello world"
        ).start()
        self.type_text = mock.patch("push_to_stt.session.type_text").start()

    def test_it_draws_a_bar_while_recording(self):
        run(self.settings)
        self.assertEqual(len(self.notify.call_args_list[1].args[1]), BAR_WIDTH)

    def test_it_takes_the_meter_down_before_transcribing(self):
        order = []
        self.close.side_effect = lambda *_: order.append("meter down")
        self.transcribe.side_effect = lambda *_, **__: (
            order.append("transcribe") or "hello"
        )
        run(self.settings)
        self.assertEqual(order, ["meter down", "transcribe"])

    def test_it_types_what_was_said(self):
        run(self.settings)
        self.type_text.assert_called_once_with("hello world")

    def test_it_deletes_the_recording_afterwards(self):
        run(self.settings)
        self.assertFalse(self.settings.wav_file.exists())

    def test_silence_types_nothing(self):
        self.transcribe.return_value = ""
        run(self.settings)
        self.type_text.assert_not_called()

    def test_a_cancelled_dictation_is_not_transcribed(self):
        """Cancel deletes the recording first, so the worker finds nothing to do."""
        self.settings.wav_file.unlink()
        run(self.settings)
        self.transcribe.assert_not_called()
        self.type_text.assert_not_called()
        self.close.assert_called_once_with(7)

    def test_an_empty_recording_is_not_transcribed(self):
        self.settings.wav_file.write_bytes(b"")
        run(self.settings)
        self.transcribe.assert_not_called()

    def test_the_recording_is_deleted_even_when_whisper_fails(self):
        self.transcribe.side_effect = RuntimeError("engine broke")
        with self.assertRaises(RuntimeError):
            run(self.settings)
        self.assertFalse(self.settings.wav_file.exists())


class SpawnTest(unittest.TestCase):
    def test_the_worker_runs_from_the_state_directory(self):
        """onnxruntime writes a telemetry file into the current directory."""
        settings = Settings(state_dir=Path("/run/user/1000/push-to-stt"))
        with mock.patch("push_to_stt.session.BackgroundProcess") as process:
            spawn(settings)
        self.assertEqual(process.return_value.start.call_args.kwargs["cwd"], settings.state_dir)


if __name__ == "__main__":
    unittest.main()
