# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from unittest import mock

from push_to_stt.desktop import (
    KEYBINDING_PATH,
    close_notification,
    notify,
    notify_progress,
    with_keybinding_path,
)

OTHER = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/"


class KeybindingListTest(unittest.TestCase):
    """GNOME stores the custom keybindings as one list, so ours must be merged in."""

    def test_adds_the_path_to_an_empty_list(self):
        self.assertEqual(with_keybinding_path("@as []"), f"['{KEYBINDING_PATH}']")

    def test_keeps_the_keybindings_of_other_tools(self):
        result = with_keybinding_path(f"['{OTHER}']\n")
        self.assertEqual(result, f"['{OTHER}', '{KEYBINDING_PATH}']")

    def test_does_not_add_the_path_twice(self):
        once = with_keybinding_path("@as []")
        self.assertEqual(with_keybinding_path(once), once)


class NotifyTest(unittest.TestCase):
    def test_a_missing_notify_send_is_not_an_error(self):
        with mock.patch(
            "push_to_stt.desktop.subprocess.run", side_effect=FileNotFoundError
        ):
            notify("hello")


class NotifyProgressTest(unittest.TestCase):
    """The meter needs a notification that stays put and can be redrawn."""

    def run_with(self, stdout="7", **kwargs):
        with mock.patch("push_to_stt.desktop.subprocess.run") as run:
            run.return_value = mock.Mock(stdout=stdout)
            returned = notify_progress("Recording", "bars", **kwargs)
        return returned, run.call_args.args[0]

    def test_it_returns_the_notification_id(self):
        returned, _ = self.run_with()
        self.assertEqual(returned, 7)

    def test_it_asks_for_a_notification_that_stays(self):
        _, command = self.run_with()
        self.assertIn("--urgency=critical", command)
        self.assertIn("--print-id", command)

    def test_it_redraws_the_same_notification(self):
        _, command = self.run_with(replace_id=7)
        self.assertEqual(command[command.index("--replace-id") + 1], "7")

    def test_the_first_call_replaces_nothing(self):
        _, command = self.run_with()
        self.assertNotIn("--replace-id", command)

    def test_an_unreadable_id_is_reported_as_none(self):
        returned, _ = self.run_with(stdout="")
        self.assertEqual(returned, 0)

    def test_a_missing_notify_send_is_not_an_error(self):
        with mock.patch(
            "push_to_stt.desktop.subprocess.run", side_effect=FileNotFoundError
        ):
            self.assertEqual(notify_progress("Recording", "bars"), 0)


class CloseNotificationTest(unittest.TestCase):
    def test_it_closes_the_notification_by_id(self):
        with mock.patch("push_to_stt.desktop.subprocess.run") as run:
            close_notification(7)
        self.assertIn("7", run.call_args.args[0])

    def test_it_does_nothing_without_an_id(self):
        with mock.patch("push_to_stt.desktop.subprocess.run") as run:
            close_notification(0)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
