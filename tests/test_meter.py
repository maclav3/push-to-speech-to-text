# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
import array
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from push_to_stt.config import Settings
from push_to_stt.meter import BAR_WIDTH, BLOCKS, HEADER_BYTES, bar, run, tail_loudness


def write_recording(path: Path, samples: list[int]) -> None:
    """Write a fake growing recording: a header we skip, then 16 bit samples."""
    body = array.array("h", samples)
    path.write_bytes(b"\0" * HEADER_BYTES + body.tobytes())


def sine(amplitude: int, count: int = 2048) -> list[int]:
    return [int(amplitude * math.sin(index / 8)) for index in range(count)]


class TailLoudnessTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.wav = Path(directory.name) / "take.wav"

    def test_a_missing_file_is_silent(self):
        self.assertEqual(tail_loudness(self.wav), 0.0)

    def test_a_header_without_audio_is_silent(self):
        self.wav.write_bytes(b"\0" * HEADER_BYTES)
        self.assertEqual(tail_loudness(self.wav), 0.0)

    def test_silence_is_zero(self):
        write_recording(self.wav, [0] * 2048)
        self.assertEqual(tail_loudness(self.wav), 0.0)

    def test_a_loud_signal_reaches_the_top(self):
        write_recording(self.wav, sine(32000))
        self.assertGreater(tail_loudness(self.wav), 0.9)

    def test_a_quiet_signal_stays_low(self):
        write_recording(self.wav, sine(60))
        self.assertLess(tail_loudness(self.wav), 0.3)

    def test_louder_audio_gives_a_higher_reading(self):
        write_recording(self.wav, sine(1000))
        quiet = tail_loudness(self.wav)
        write_recording(self.wav, sine(16000))
        self.assertGreater(tail_loudness(self.wav), quiet)

    def test_only_the_end_of_the_recording_counts(self):
        """The meter must follow the voice now, not the average since the start."""
        write_recording(self.wav, sine(32000, 40000) + [0] * 4096)
        self.assertEqual(tail_loudness(self.wav), 0.0)

    def test_an_odd_byte_count_does_not_crash(self):
        write_recording(self.wav, [0] * 2048)
        with self.wav.open("ab") as growing:
            growing.write(b"\x01")
        self.assertEqual(tail_loudness(self.wav), 0.0)

    def test_the_reading_never_leaves_the_range(self):
        for amplitude in (0, 1, 300, 12000, 32767):
            write_recording(self.wav, sine(amplitude))
            reading = tail_loudness(self.wav)
            self.assertGreaterEqual(reading, 0.0)
            self.assertLessEqual(reading, 1.0)


class BarTest(unittest.TestCase):
    def test_silence_draws_the_lowest_block(self):
        self.assertEqual(bar([0.0] * BAR_WIDTH), BLOCKS[0] * BAR_WIDTH)

    def test_a_full_signal_draws_the_tallest_block(self):
        self.assertEqual(bar([1.0] * BAR_WIDTH), BLOCKS[-1] * BAR_WIDTH)

    def test_the_bar_keeps_its_width_when_history_is_short(self):
        self.assertEqual(len(bar([1.0])), BAR_WIDTH)

    def test_the_newest_level_sits_on_the_right(self):
        drawn = bar([0.0] * (BAR_WIDTH - 1) + [1.0])
        self.assertEqual(drawn[-1], BLOCKS[-1])
        self.assertEqual(drawn[0], BLOCKS[0])

    def test_a_louder_level_draws_a_taller_block(self):
        quiet = bar([0.2] * BAR_WIDTH)
        loud = bar([0.8] * BAR_WIDTH)
        self.assertGreater(BLOCKS.index(loud[0]), BLOCKS.index(quiet[0]))


class RunTest(unittest.TestCase):
    """The loop redraws one notification until it is interrupted."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(mock.patch.stopall)
        self.settings = Settings(state_dir=Path(directory.name))

        self.notify = mock.patch(
            "push_to_stt.meter.notify_progress", return_value=7
        ).start()
        self.close = mock.patch("push_to_stt.meter.close_notification").start()
        mock.patch("push_to_stt.meter.tail_loudness", return_value=0.5).start()
        # The loop only ends when it is interrupted, as the stop command does.
        mock.patch(
            "push_to_stt.meter.time.sleep", side_effect=[None, None, KeyboardInterrupt]
        ).start()

    def test_it_redraws_the_first_notification(self):
        run(self.settings)
        replace_ids = [
            call.kwargs.get("replace_id") for call in self.notify.call_args_list
        ]
        self.assertIsNone(replace_ids[0])
        self.assertEqual(set(replace_ids[1:]), {7})

    def test_it_draws_a_bar_of_the_right_width(self):
        run(self.settings)
        self.assertEqual(len(self.notify.call_args.args[1]), BAR_WIDTH)

    def test_it_closes_the_notification_when_interrupted(self):
        run(self.settings)
        self.close.assert_called_once_with(7)


if __name__ == "__main__":
    unittest.main()
