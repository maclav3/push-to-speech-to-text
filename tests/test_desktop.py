import unittest
from unittest import mock

from push_to_stt.desktop import KEYBINDING_PATH, notify, with_keybinding_path

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
        with mock.patch("push_to_stt.desktop.subprocess.run",
                                 side_effect=FileNotFoundError):
            notify("hello")


if __name__ == "__main__":
    unittest.main()
