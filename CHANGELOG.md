# CHANGELOG


## v0.2.2 (2026-09-15)

### Bug Fixes

- Run the worker from our own directory
  ([`4e82d7c`](https://github.com/maclav3/push-to-speech-to-text/commit/4e82d7c0139eb54b96535e2c6e07dfbe449a0833))

onnxruntime fails to open its telemetry database, falls back to SQLite's in-memory database, and
  writes a file named ":memory:.ses" into the current directory. That left litter in whichever
  project directory the hotkey fired from.

The worker now runs from the state directory under XDG_RUNTIME_DIR, which the session clears on
  logout.

### Performance Improvements

- Decode greedily and use every core
  ([`af7decc`](https://github.com/maclav3/push-to-speech-to-text/commit/af7decca5cdc21253bd7a18422477dbc1af37ab1))

Whisper searched five candidate transcriptions by default. For dictation the first is almost always
  the one that gets typed, and dropping the other four saves about 0.35 seconds on a short phrase.

Loading now uses every core, which halves the load time on this machine.

Splitting load_model out of transcribe lets a caller load the model in advance and hand it over.

- Load Whisper while you speak
  ([`f7c8c2d`](https://github.com/maclav3/push-to-speech-to-text/commit/f7c8c2dbdf490a3ddec222c2d96da9bed4e199b8))

Loading the model cost about a second of the wait after the hotkey. The worker now starts loading as
  soon as the recording begins, so the load finishes while the user is still talking.

Measured on a four second phrase, the wait after the stop press falls from about 3.8 to 2.0 seconds.
  What remains is transcription itself.

load_model now reports failures as DictationError. The worker writes to /dev/null, so an unwrapped
  error would kill it without telling anyone.

### Refactoring

- Let a background worker transcribe and type
  ([`f004de2`](https://github.com/maclav3/push-to-speech-to-text/commit/f004de2cee2359b8317bb8d602504bb5c067471f))

The stop command used to hold the hotkey for the whole of Whisper's work. Now it ends the recording,
  signals the worker and exits in under 0.2 seconds.

The worker already existed to draw the level meter, so it only gains the work that follows the
  recording. The meter module is left with the measuring.

Two orderings matter and are covered by tests. Stop must close the recording before signalling, and
  cancel must delete it before signalling.


## v0.2.1 (2026-09-15)

### Bug Fixes

- Keep argparse internals out of the help
  ([`d0035a3`](https://github.com/maclav3/push-to-speech-to-text/commit/d0035a3b69c4ebb6bf4fc1ea500fbafe8a2bf9fd))

Argparse prints help=SUPPRESS literally for a subcommand, so the internal meter command showed up as
  "==SUPPRESS==". A subcommand with no help text is left out of the list instead.


## v0.2.0 (2026-09-15)

### Documentation

- Describe the recording indicator
  ([`852f89b`](https://github.com/maclav3/push-to-speech-to-text/commit/852f89b090b4ef900b71a736d2c69b957e9e4735))

The README now says what the meter looks like and why it is a notification rather than a floating
  window. A flat bar means the wrong microphone, so that gets a line too.

### Features

- Measure the recording level and draw it as blocks
  ([`8a4cff9`](https://github.com/maclav3/push-to-speech-to-text/commit/8a4cff91c16b723810c8e5d47d613f13f8449a20))

The meter reads the tail of the file the recorder is already writing, so it needs no second capture
  stream and cannot disturb the recording.

Loudness is reported in decibels against a floor of -50 dB. A linear scale barely moves for speech,
  because the ear hears loudness logarithmically.

- Show a live level meter while recording
  ([`6a360a8`](https://github.com/maclav3/push-to-speech-to-text/commit/6a360a8dc393dbc8fedf173cda60b30c3b955eda))

GNOME draws its own notifications above every window, which is the only way an ordinary program can
  put something on top on Wayland. The meter redraws one critical notification about eight times a
  second.

The meter runs in its own process beside the recorder, because the start command exits at once. It
  comes down in a finally block, so a failed recording cannot leave it stuck on screen.

### Refactoring

- Extract BackgroundProcess from Recorder
  ([`95ee6ae`](https://github.com/maclav3/push-to-speech-to-text/commit/95ee6ae440896bd5cf39fe8b0ef6b9988fa6b694))

The recorder tracks a detached process through a PID file. The recording indicator needs the same
  handling, so the mechanism moves into its own class rather than being written twice.

Recorder keeps only what is specific to it: the arecord command line, and what counts as a usable
  recording.


## v0.1.1 (2026-09-15)

### Chores

- Relicense under the GPL version 3 or later
  ([`986ac0e`](https://github.com/maclav3/push-to-speech-to-text/commit/986ac0e240e0c83317cd9f5b4af4ca5c4fb6a674))

A changed version of this tool must now stay open. MIT allowed anyone to take it closed, which is
  not what I want for it.

The GPL text names no copyright holder, so COPYRIGHT carries my notice next to it. Every source file
  carries an SPDX tag, which states the same thing in two lines that tools can read.

The SPDX licence field needs setuptools 77, so the build requirement moves up with it.


## v0.1.0 (2026-09-15)

### Build System

- Add ruff and a Taskfile for local checks
  ([`cb69580`](https://github.com/maclav3/push-to-speech-to-text/commit/cb69580f25d54320550e057d8ef81e03667e12b9))

Task gives the same entry points as my other Python projects: venv, fmt, lint and install. The check
  task runs what CI runs, so a failure shows up before the push.

Ruff replaces both black and flake8 here. One tool covers formatting and linting, so the dev extra
  stays at a single package.

### Code Style

- Format the code with ruff
  ([`3bf61c1`](https://github.com/maclav3/push-to-speech-to-text/commit/3bf61c15b230fcba4d7442b997a7f5161c5b0390))

Mechanical. The only hand edit is a nested with statement in the recorder tests, which ruff combined
  into one parenthesised block.

- Keep each arecord flag next to its value
  ([`f51fa44`](https://github.com/maclav3/push-to-speech-to-text/commit/f51fa44e26fbe12db89eaba6aa1cf867a321bf6f))

The formatter split the argument list into one item per line, which separated every flag from the
  value it takes. Building the list in pairs reads the same way the command line does, and the
  formatter leaves it alone.

### Continuous Integration

- Release with python-semantic-release
  ([`5e64382`](https://github.com/maclav3/push-to-speech-to-text/commit/5e64382991dedb2f32e097d72898911df9c0e5bf))

A push to main now derives the next version from the commit messages, writes the changelog and tags
  the release. The tag table matches my other Python project, so the same commit style produces the
  same bumps.

The version lives in two files. Semantic release keeps pyproject.toml and the package __version__ in
  step, so they cannot drift.

- Run lint and tests on a Python matrix
  ([`4e3c374`](https://github.com/maclav3/push-to-speech-to-text/commit/4e3c37436eb788dab2ca14317af53d92b07a937d))

The build job installs the package the way a user does, then lints, runs the tests and calls the
  console script. Installing rather than importing from the checkout means the job also proves the
  packaging.

Local and CI checks now match, because task lint gained the same format check.

### Documentation

- Describe the uinput permission precisely
  ([`8e975e8`](https://github.com/maclav3/push-to-speech-to-text/commit/8e975e8d308230465908044705adbfe2db2e443c))

The note claimed that setup exposes every input device. It does not. Reading input devices comes
  from membership of the input group, which most desktops grant already. Setup only adds write
  access to /dev/uinput, which allows typing, not reading.

- Document the pipx install and the development tasks
  ([`6f60f3f`](https://github.com/maclav3/push-to-speech-to-text/commit/6f60f3f2c477cbf4cb4c7cfb24c88acff7cee428))

The install line now points at the git URL, so the README works for someone who has not cloned the
  repository. The development section lists the tasks and says which checks CI runs.

Commit messages drive the release, so the section asks for conventional commits.

### Features

- Add push-to-stt, hotkey dictation for Linux
  ([`e59a68a`](https://github.com/maclav3/push-to-speech-to-text/commit/e59a68a39caa210214a5ba3629a6a5fd5efef90b))

A hotkey starts arecord, a second press stops it. faster-whisper transcribes the recording and
  ydotool types the result into the focused field.

GNOME shortcuts report key press only, so the tool toggles rather than using push-to-talk, and the
  recorder outlives the process that starts it. A PID file in the runtime directory joins the two
  presses.

wtype cannot work under Mutter, which does not offer the virtual keyboard protocol, so typing goes
  through ydotool and uinput.

The tests replace subprocess and os.kill, so the suite needs no microphone, no keyboard and no model
  download.

### Refactoring

- Move the package under src/
  ([`7ecca4e`](https://github.com/maclav3/push-to-speech-to-text/commit/7ecca4e291b422cf3bc013713a605f820d0bb692))

The src layout keeps the package off sys.path when running from the checkout. The tests then import
  the installed package, which is what users get, instead of the source tree next to them.

This also matches the layout of my other Python projects.
