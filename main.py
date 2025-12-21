#!/usr/bin/env python3
"""
Entry point for the powerlifting video comparison tool.

This script delegates all processing to :mod:`video_editor` so IDEs like
PyCharm can run it with predefined defaults or custom CLI arguments.
"""

from __future__ import annotations

import sys

from video_editor import (
    INTERACTIVE_PROMPT,
    PYCHARM_DEFAULTS,
    build_args_interactively,
    run_cli,
)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(run_cli(sys.argv[1:]))

    if INTERACTIVE_PROMPT:
        raise SystemExit(run_cli(build_args_interactively()))

    raise SystemExit(run_cli(PYCHARM_DEFAULTS))
