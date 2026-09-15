# push-to-speech-to-text

Dictate into any text field on Linux. Press a hotkey, speak, press it again.

```
hotkey -> arecord -> faster-whisper -> ydotool types into the focused field
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
pipx install .
push-to-stt setup
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

The recorder must outlive the process that starts it, because the next hotkey
press arrives in a new process. A PID file in `$XDG_RUNTIME_DIR` joins the two.

## Test

```bash
python3 -m unittest discover -s tests -t .
```

The tests replace `subprocess` and `os.kill`, so they need no microphone, no
keyboard and no model. They run in well under a second.

## Known limits

- Each dictation loads the Whisper model again, which costs a second or two. A background service would keep it warm.
- `wtype` cannot work on GNOME, because Mutter does not offer the virtual keyboard protocol. That is why this uses `ydotool`.
- Membership of the `input` group lets any program on your account read all input devices.

## Licence

MIT. See `LICENSE`.
