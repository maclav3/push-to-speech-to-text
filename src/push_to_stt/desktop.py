# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
"""Desktop integration: notifications, /dev/uinput access, and the GNOME hotkey."""

from __future__ import annotations

import ast
import getpass
import grp
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import DictationError, missing_program

NOTIFY_TAG = "string:x-canonical-private-synchronous:push-to-stt"
NOTIFY_SERVICE = "org.freedesktop.Notifications"
NOTIFY_OBJECT = "/org/freedesktop/Notifications"
UINPUT_DEVICE = Path("/dev/uinput")
UDEV_RULE_PATH = Path("/etc/udev/rules.d/99-uinput-push-to-stt.rules")
UDEV_RULE = (
    'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"'
)

SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
KEYBINDING_PATH = (
    "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/push-to-stt/"
)
DEFAULT_HOTKEY = "<Control><Alt>space"


def notify(summary: str, body: str = "") -> None:
    """Show a desktop message. A missing notify-send is not worth an error."""
    try:
        # The tag replaces the previous popup instead of stacking popups.
        subprocess.run(["notify-send", "-h", NOTIFY_TAG, summary, body], check=False)
    except FileNotFoundError:
        pass


def notify_progress(summary: str, body: str, replace_id: int = 0) -> int:
    """Show a notification that stays on screen, and return its id.

    GNOME draws its own notifications above every window, which is the only way
    an ordinary program can put something on top on Wayland. Critical urgency
    stops the banner from fading after a few seconds.
    """
    command = [
        "notify-send",
        "--urgency=critical",
        "--print-id",
        "--app-name=push-to-stt",
    ]
    if replace_id:
        command += ["--replace-id", str(replace_id)]
    command += [summary, body]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def close_notification(notification_id: int) -> None:
    """Take the notification off the screen at once, without waiting for a timeout."""
    if not notification_id:
        return
    try:
        subprocess.run(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                NOTIFY_SERVICE,
                "--object-path",
                NOTIFY_OBJECT,
                "--method",
                f"{NOTIFY_SERVICE}.CloseNotification",
                str(notification_id),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        pass


def launch_command() -> str:
    """The command a hotkey should run to toggle dictation."""
    installed = shutil.which("push-to-stt")
    if installed:
        return f"{installed} toggle"
    return f"{sys.executable} -m push_to_stt toggle"


def grant_uinput_access() -> None:
    """Let ydotool write to /dev/uinput. This needs sudo once."""
    if os.access(UINPUT_DEVICE, os.W_OK):
        print(f"{UINPUT_DEVICE} is already writable.")
        return
    print(f"ydotool needs write access to {UINPUT_DEVICE}. This asks for sudo.")
    _sudo(["tee", str(UDEV_RULE_PATH)], input=UDEV_RULE + "\n")
    _sudo(["udevadm", "control", "--reload-rules"])
    _sudo(["udevadm", "trigger", "--name-match=uinput"])
    if not _in_input_group():
        _sudo(["usermod", "--append", "--groups", "input", getpass.getuser()])
        print("Log out and back in, so that you join the input group.")


def bind_hotkey(hotkey: str = DEFAULT_HOTKEY) -> None:
    """Point a GNOME custom shortcut at this tool."""
    if not shutil.which("gsettings"):
        print(f"gsettings not found. Bind this command by hand: {launch_command()}")
        return
    current = _gsettings_get(SCHEMA, "custom-keybindings")
    _gsettings_set(SCHEMA, "custom-keybindings", with_keybinding_path(current))

    schema = f"{SCHEMA}.custom-keybinding:{KEYBINDING_PATH}"
    _gsettings_set(schema, "name", "Push to speech to text")
    _gsettings_set(schema, "command", launch_command())
    _gsettings_set(schema, "binding", hotkey)
    print(f"Hotkey set to {hotkey}.")


def with_keybinding_path(current: str, path: str = KEYBINDING_PATH) -> str:
    """Add our path to the list of custom keybindings that gsettings printed.

    GNOME prints an empty list as the typed literal "@as []". A filled list uses
    Python's own syntax for a list of strings, so it parses and prints directly.
    """
    text = current.strip()
    paths = [] if text in ("", "@as []") else list(ast.literal_eval(text))
    if path not in paths:
        paths.append(path)
    return repr(paths)


def _in_input_group() -> bool:
    try:
        return grp.getgrnam("input").gr_gid in os.getgroups()
    except KeyError:
        return False


def _sudo(command: list[str], input: str | None = None) -> None:
    try:
        subprocess.run(
            ["sudo", *command],
            input=input,
            text=True,
            stdout=subprocess.DEVNULL,
            check=True,
        )
    except FileNotFoundError:
        raise missing_program("sudo") from None
    except subprocess.CalledProcessError as error:
        raise DictationError(f"Command failed: sudo {' '.join(command)}") from error


def _gsettings_get(schema: str, key: str) -> str:
    return subprocess.run(
        ["gsettings", "get", schema, key], capture_output=True, text=True, check=True
    ).stdout


def _gsettings_set(schema: str, key: str, value: str) -> None:
    subprocess.run(["gsettings", "set", schema, key, value], check=True)
