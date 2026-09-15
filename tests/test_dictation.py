# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import signal
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from push_to_stt import DictationError
from push_to_stt.config import Settings
from push_to_stt.dictation import Recorder, load_model, transcribe, type_text

from .fakes import FakeProcessTable


class RecorderTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.settings = Settings(state_dir=Path(directory.name) / "push-to-stt")
        self.table = FakeProcessTable()
        self.recorder = Recorder(self.settings)

        kill = mock.patch("push_to_stt.background.os.kill", self.table.kill)
        kill.start()
        self.addCleanup(kill.stop)

        self.popen = mock.patch(
            "push_to_stt.background.subprocess.Popen", side_effect=self.fake_popen
        ).start()
        self.addCleanup(mock.patch.stopall)

    def fake_popen(self, command, **kwargs):
        """Pretend arecord started and wrote its file."""
        Path(command[-1]).write_bytes(b"RIFF fake wav")
        self.table.alive.add(4242)
        return mock.Mock(pid=4242)

    def test_start_records_the_pid_of_the_recorder(self):
        self.recorder.start()
        self.assertEqual(self.settings.pid_file.read_text(), "4242")
        self.assertTrue(self.recorder.is_recording)

    def test_start_asks_for_sixteen_kilohertz_mono(self):
        self.recorder.start()
        command = self.popen.call_args.args[0]
        self.assertEqual(command[0], "arecord")
        self.assertIn("16000", command)
        self.assertEqual(command[command.index("--channels") + 1], "1")

    def test_start_passes_the_chosen_audio_device(self):
        Recorder(
            Settings(state_dir=self.settings.state_dir, audio_device="hw:1,0")
        ).start()
        command = self.popen.call_args.args[0]
        self.assertEqual(command[command.index("--device") + 1], "hw:1,0")

    def test_start_twice_is_refused(self):
        self.recorder.start()
        with self.assertRaises(DictationError):
            self.recorder.start()

    def test_a_missing_arecord_names_the_package(self):
        self.popen.side_effect = FileNotFoundError
        with self.assertRaises(DictationError) as caught:
            self.recorder.start()
        self.assertIn("alsa-utils", str(caught.exception))

    def test_stop_interrupts_the_recorder_and_returns_the_audio(self):
        self.recorder.start()
        wav = self.recorder.stop()
        # SIGINT, not SIGKILL, or arecord leaves the WAV header unwritten.
        self.assertEqual(self.table.signals[-1], (4242, signal.SIGINT))
        self.assertEqual(wav, self.settings.wav_file)
        self.assertFalse(self.settings.pid_file.exists())

    def test_stop_without_a_recording_is_refused(self):
        with self.assertRaises(DictationError):
            self.recorder.stop()

    def test_stop_refuses_an_empty_recording(self):
        self.recorder.start()
        self.settings.wav_file.write_bytes(b"")
        with self.assertRaises(DictationError):
            self.recorder.stop()

    def test_cancel_throws_the_audio_away(self):
        self.recorder.start()
        self.recorder.cancel()
        self.assertFalse(self.settings.wav_file.exists())
        self.assertFalse(self.settings.pid_file.exists())
        self.assertFalse(self.recorder.is_recording)

    def test_cancel_without_a_recording_does_nothing(self):
        self.recorder.cancel()


class TypeTextTest(unittest.TestCase):
    def test_the_text_goes_to_ydotool_on_standard_input(self):
        with mock.patch("push_to_stt.dictation.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0)
            type_text("hello")
        self.assertEqual(run.call_args.args[0][:2], ["ydotool", "type"])
        self.assertEqual(run.call_args.kwargs["input"], "hello")

    def test_a_missing_ydotool_names_the_package(self):
        with (
            mock.patch(
                "push_to_stt.dictation.subprocess.run", side_effect=FileNotFoundError
            ),
            self.assertRaises(DictationError) as caught,
        ):
            type_text("hello")
        self.assertIn("apt install ydotool", str(caught.exception))

    def test_a_failure_points_at_the_setup_command(self):
        with mock.patch("push_to_stt.dictation.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=1)
            with self.assertRaises(DictationError) as caught:
                type_text("hello")
        self.assertIn("setup", str(caught.exception))


if __name__ == "__main__":
    unittest.main()


class TranscribeTest(unittest.TestCase):
    """Speed settings that a user would never see, but always feel."""

    def setUp(self) -> None:
        self.settings = Settings(state_dir=Path("/nowhere"))
        self.whisper = mock.patch("faster_whisper.WhisperModel").start()
        self.addCleanup(mock.patch.stopall)
        self.model = self.whisper.return_value
        self.model.transcribe.return_value = ([mock.Mock(text=" hello ")], None)

    def test_the_model_uses_every_core(self):
        load_model(self.settings)
        self.assertEqual(self.whisper.call_args.kwargs["cpu_threads"], os.cpu_count())
        self.assertEqual(self.whisper.call_args.kwargs["compute_type"], "int8")

    def test_decoding_takes_the_first_candidate(self):
        """Searching five candidates costs time and rarely changes the words."""
        transcribe(Path("take.wav"), self.settings)
        self.assertEqual(self.model.transcribe.call_args.kwargs["beam_size"], 1)

    def test_silence_is_filtered_out(self):
        transcribe(Path("take.wav"), self.settings)
        self.assertTrue(self.model.transcribe.call_args.kwargs["vad_filter"])

    def test_a_ready_model_is_reused_instead_of_loaded(self):
        """The session loads the model while you speak, then hands it over."""
        ready = mock.Mock()
        ready.transcribe.return_value = ([mock.Mock(text="hello")], None)
        transcribe(Path("take.wav"), self.settings, model=ready)
        self.whisper.assert_not_called()

    def test_the_text_is_trimmed(self):
        self.assertEqual(transcribe(Path("take.wav"), self.settings), "hello")
