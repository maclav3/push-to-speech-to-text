import tempfile
import unittest
from pathlib import Path

from push_to_stt.config import DEFAULT_MODEL, Settings


class SettingsFromEnvTest(unittest.TestCase):
    def test_uses_the_runtime_directory_for_state(self):
        settings = Settings.from_env({"XDG_RUNTIME_DIR": "/run/user/1000"})
        self.assertEqual(settings.state_dir, Path("/run/user/1000/push-to-stt"))
        self.assertEqual(settings.pid_file.name, "recorder.pid")
        self.assertEqual(settings.wav_file.name, "take.wav")

    def test_falls_back_to_the_temporary_directory(self):
        settings = Settings.from_env({})
        self.assertEqual(settings.state_dir.parent, Path(tempfile.gettempdir()))

    def test_defaults_leave_the_language_unset(self):
        settings = Settings.from_env({})
        self.assertEqual(settings.model, DEFAULT_MODEL)
        self.assertIsNone(settings.language)
        self.assertIsNone(settings.audio_device)

    def test_reads_every_override(self):
        settings = Settings.from_env({
            "STT_MODEL": "medium",
            "STT_LANGUAGE": "pl",
            "STT_AUDIO_DEVICE": "hw:1,0",
        })
        self.assertEqual(settings.model, "medium")
        self.assertEqual(settings.language, "pl")
        self.assertEqual(settings.audio_device, "hw:1,0")

    def test_an_empty_variable_counts_as_unset(self):
        settings = Settings.from_env({"STT_MODEL": "", "STT_LANGUAGE": ""})
        self.assertEqual(settings.model, DEFAULT_MODEL)
        self.assertIsNone(settings.language)
