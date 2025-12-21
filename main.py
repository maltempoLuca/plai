#!/usr/bin/env python3
"""
Entry point for the powerlifting video comparison tool.

This script delegates all processing to :mod:`video_editor` so IDEs like
PyCharm can run it with predefined defaults or custom CLI arguments.
"""

from __future__ import annotations

import sys

from video_editor import INTERACTIVE_PROMPT, build_args_interactively, run_cli

# Default arguments for quick runs from PyCharm (kept out of the library module).
PYCHARM_DEFAULTS = [
    "--start_mode", "sync",
    "--video", r"./input/W4 - 142.5.mp4", "--start", "10.45", "--label", "W4",
    "--video", r"./input/W5 - 142.5.mp4", "--start", "11.45", "--label", "W5",
    "--output", r"./output/squat_comparison_2.mp4",
    "--audio", "video2",
    "--fps", "60",
    "--overwrite",
]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(run_cli(sys.argv[1:]))

    if INTERACTIVE_PROMPT:
        raise SystemExit(run_cli(build_args_interactively()))

    raise SystemExit(run_cli(PYCHARM_DEFAULTS))
