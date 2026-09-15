# CHANGELOG


## v0.1.1 (2026-09-15)

### Chores

- Relicense under the GPL version 3 or later
  ([`b4b0be6`](https://github.com/maclav3/push-to-speech-to-text/commit/b4b0be692b56a0add8087472b20e4d377c88e5d6))

A changed version of this tool must now stay open. MIT allowed anyone to take it closed, which is
  not what I want for it.

The GPL text names no copyright holder, so COPYRIGHT carries my notice next to it. Every source file
  carries an SPDX tag, which states the same thing in two lines that tools can read.

The SPDX licence field needs setuptools 77, so the build requirement moves up with it.


## v0.1.0 (2026-09-15)

### Build System

- Add ruff and a Taskfile for local checks
  ([`0a3fc3a`](https://github.com/maclav3/push-to-speech-to-text/commit/0a3fc3ae8578bfdb71288df2537d8c541f14b47c))

Task gives the same entry points as my other Python projects: venv, fmt, lint and install. The check
  task runs what CI runs, so a failure shows up before the push.

Ruff replaces both black and flake8 here. One tool covers formatting and linting, so the dev extra
  stays at a single package.

### Code Style

- Format the code with ruff
  ([`11ed11c`](https://github.com/maclav3/push-to-speech-to-text/commit/11ed11c17e0cfabceb8ae17361af7d2969e605d5))

Mechanical. The only hand edit is a nested with statement in the recorder tests, which ruff combined
  into one parenthesised block.

- Keep each arecord flag next to its value
  ([`ed8db73`](https://github.com/maclav3/push-to-speech-to-text/commit/ed8db730038d5dfd8ac8b38959b31fe076ee9272))

The formatter split the argument list into one item per line, which separated every flag from the
  value it takes. Building the list in pairs reads the same way the command line does, and the
  formatter leaves it alone.

### Continuous Integration

- Release with python-semantic-release
  ([`a3d2818`](https://github.com/maclav3/push-to-speech-to-text/commit/a3d2818433b59fa8f36e0ffbde81c5a7c4a169e3))

A push to main now derives the next version from the commit messages, writes the changelog and tags
  the release. The tag table matches my other Python project, so the same commit style produces the
  same bumps.

The version lives in two files. Semantic release keeps pyproject.toml and the package __version__ in
  step, so they cannot drift.

- Run lint and tests on a Python matrix
  ([`33753d5`](https://github.com/maclav3/push-to-speech-to-text/commit/33753d52259061be02cb1e2f9b9c163d8423aba1))

The build job installs the package the way a user does, then lints, runs the tests and calls the
  console script. Installing rather than importing from the checkout means the job also proves the
  packaging.

Local and CI checks now match, because task lint gained the same format check.

### Documentation

- Describe the uinput permission precisely
  ([`7093814`](https://github.com/maclav3/push-to-speech-to-text/commit/70938148269af3d3cee997abcf0ad8cdf1f5b6fd))

The note claimed that setup exposes every input device. It does not. Reading input devices comes
  from membership of the input group, which most desktops grant already. Setup only adds write
  access to /dev/uinput, which allows typing, not reading.

- Document the pipx install and the development tasks
  ([`6c175d8`](https://github.com/maclav3/push-to-speech-to-text/commit/6c175d89c054a0810af1e43f211315b8f6517921))

The install line now points at the git URL, so the README works for someone who has not cloned the
  repository. The development section lists the tasks and says which checks CI runs.

Commit messages drive the release, so the section asks for conventional commits.

### Features

- Add push-to-stt, hotkey dictation for Linux
  ([`0327afe`](https://github.com/maclav3/push-to-speech-to-text/commit/0327afe45476678cb266cf12589fe79a772a5d6d))

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
  ([`5488a05`](https://github.com/maclav3/push-to-speech-to-text/commit/5488a05cb37d78f2af1459f60b5a64159cd498f2))

The src layout keeps the package off sys.path when running from the checkout. The tests then import
  the installed package, which is what users get, instead of the source tree next to them.

This also matches the layout of my other Python projects.
