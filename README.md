# push-to-speech-to-text

[![CI](https://github.com/maclav3/push-to-speech-to-text/actions/workflows/ci.yml/badge.svg)](https://github.com/maclav3/push-to-speech-to-text/actions/workflows/ci.yml)

Dictate into any text field on Linux. Press a hotkey, speak, press it again.

```
hotkey -> arecord -> faster-whisper -> ydotool types into the focused field
            |
            +-> a live level meter, on top of your windows
```

Whisper runs on your machine. No cloud service, no API key.

## Why a toggle and not push-to-talk

GNOME custom shortcuts fire on key press only. They never report key release.
So the first press starts the recording and the second press ends it.

## Requirements

- Linux with Python 3.10 or newer
- `arecord`: `sudo apt install alsa-utils`
- `ydotool`: `sudo apt install ydotool`

## Install

```bash
pipx install git+https://github.com/maclav3/push-to-speech-to-text.git
push-to-stt setup
```

If you do not have `pipx`, install it first:

```bash
pip install --user pipx
pipx ensurepath
```

`setup` does two things:

1. Grants `/dev/uinput` access to the `input` group, so `ydotool` can type. This needs sudo.
2. Binds `<Control><Alt>space` to `push-to-stt toggle` in GNOME.

Choose another key with `push-to-stt setup --hotkey '<Super>x'`.

The first transcription downloads the model. Later runs use the cached copy.

## Use

| Command | Effect |
|---|---|
| `push-to-stt` | Start recording, or stop and type the text |
| `push-to-stt start` | Start recording |
| `push-to-stt stop` | Stop, transcribe, type |
| `push-to-stt cancel` | Stop and throw the audio away |

`toggle` is the default, so the bare command does the same as `push-to-stt toggle`.

## The recording indicator

While recording, a notification stays on screen and shows the sound level:

```
Recording
▁▁▂▃▅▇█▇▅▃▂▁
```

The bar scrolls, newest on the right, and redraws about eight times a second.
If it stays flat while you speak, the wrong microphone is selected. Set
`STT_AUDIO_DEVICE` to choose another one.

The level is read from the recording itself, not from a second capture stream.
So the meter cannot disturb what Whisper hears.

A notification is used because GNOME draws its own notifications above every
window. On Wayland an ordinary program cannot place a window on top.

## Settings

Set these as environment variables.

| Variable | Default | Meaning |
|---|---|---|
| `STT_MODEL` | `small` | Whisper model. `base` is faster, `medium` is more accurate. |
| `STT_LANGUAGE` | auto | Force a language, for example `en` or `pl`. |
| `STT_AUDIO_DEVICE` | default | ALSA device for `arecord`, for example `hw:1,0`. |

A GNOME shortcut does not read your shell profile. Put the variables in
`~/.config/environment.d/push-to-stt.conf` instead.

## How the code is arranged

| Module | Holds |
|---|---|
| `config.py` | The `Settings` dataclass, read from the environment once |
| `dictation.py` | The `Recorder`, the Whisper call, and the typing |
| `desktop.py` | Notifications, `/dev/uinput` access, the GNOME hotkey |
| `cli.py` | Argument parsing and the order of the steps |
| `meter.py` | The level reading, the bar, and the loop that redraws it |
| `background.py` | A process that outlives the command which started it |

The recorder must outlive the process that starts it, because the next hotkey
press arrives in a new process. A PID file in `$XDG_RUNTIME_DIR` joins the two.
The meter runs the same way, with a PID file of its own.

## Development

```bash
git clone https://github.com/maclav3/push-to-speech-to-text.git
cd push-to-speech-to-text
task venv
```

The tasks need [Task](https://taskfile.dev/).

| Task | Effect |
|---|---|
| `task venv` | Create `.venv` and install the package with its dev tools |
| `task fmt` | Format the code with ruff |
| `task lint` | Check style and formatting |
| `task test` | Run the tests |
| `task check` | Lint and test, exactly as CI does |
| `task install` | Install into the environment you are already in |

The tests replace `subprocess` and `os.kill`, so they need no microphone, no
keyboard and no model. They run in well under a second.

CI runs the same checks on Python 3.10, 3.11 and 3.12. A push to `main` then
releases a new version, taken from the commit messages, so please write them
in the [conventional commits](https://www.conventionalcommits.org/) style.

## Known limits

- Each dictation loads the Whisper model again, which costs a second or two. A background service would keep it warm.
- `wtype` cannot work on GNOME, because Mutter does not offer the virtual keyboard protocol. That is why this uses `ydotool`.
- The indicator is a notification, so it sits where GNOME puts notifications. A free-floating dot would need a GNOME Shell extension.
- `setup` gives the `input` group write access to `/dev/uinput`. Any program that runs as you can then type into any window.
- Many desktops already put you in the `input` group. That membership already allows reading every input device, which is the larger exposure.

## Licence

GNU General Public License, version 3 or later. See `LICENSE`.

You may use, change and share this program. If you share a changed version,
you must share its source under the same licence.
