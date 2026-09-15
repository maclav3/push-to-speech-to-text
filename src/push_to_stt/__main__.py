# SPDX-FileCopyrightText: 2026 Maciej Bratek
# SPDX-License-Identifier: GPL-3.0-or-later
"""Entry point for `python -m push_to_stt`."""

import sys

from .cli import main

sys.exit(main())
