#!/usr/bin/env python3
"""
Entry point for the powerlifting side-by-side video comparison tool.

This script builds a SideBySideComparisonRequest and delegates all processing
to video_editor.export_side_by_side_comparison().
"""

from __future__ import annotations
from video_editor import SideBySideComparisonRequest, StartMode, export_side_by_side_comparison

def build_request() -> SideBySideComparisonRequest:
    return SideBySideComparisonRequest(
        start_mode=StartMode.SYNC,
        videos=[
            r"./input/W4 - 142.5.mp4",
            r"./input/W5 - 142.5.mp4",
            r"./input/W6 - 145.mp4",
        ],
        starts=[10.45, 11.45, 9.15],
        labels=["W4 - 142.5", "W5 - 142.5", "W6 - 145"],
        output=r"./output/squat_comparison_3.mp4",
        audio="video3",
        fps=60.0,
        overwrite=True,
    )


if __name__ == "__main__":
    raise SystemExit(export_side_by_side_comparison(build_request()))
